import re
from html.parser import HTMLParser


class AccessibilityAuditor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.violations = []
        self.passes = []
        self.tags = []
        self.headings = []
        self.has_html_lang = False
        self.has_title = False
        self.title_text = ''
        self.has_main = False
        self.has_skip_link = False
        self.in_title = False
        self.in_label = 0
        self.in_button = False
        self.current_button_text = ''
        self.current_button_attrs = {}

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tags.append((tag, attr_dict))

        if tag == 'label':
            self.in_label += 1

        elif tag == 'html':
            if 'lang' in attr_dict and attr_dict['lang'].strip():
                self.has_html_lang = True
                self.passes.append(('html_lang', '<html> element has valid lang attribute.'))
            else:
                self.violations.append(('html_lang', '<html> element is missing a lang attribute.'))

        elif tag == 'title':
            self.in_title = True

        elif tag == 'main' or attr_dict.get('role') == 'main':
            self.has_main = True

        elif tag == 'a':
            href = attr_dict.get('href', '')
            if href.startswith('#') and 'skip' in attr_dict.get('class', '').lower():
                self.has_skip_link = True
            elif href.startswith('#main') or href.startswith('#content'):
                self.has_skip_link = True

        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            self.headings.append(level)

        elif tag == 'img':
            if 'alt' in attr_dict:
                self.passes.append(('image_alt', f'Image {attr_dict.get("src", "")} has alt attribute.'))
            else:
                self.violations.append(('image_alt', f'Image {attr_dict.get("src", "")} is missing an alt attribute.'))

        elif tag in ('input', 'select', 'textarea'):
            input_type = attr_dict.get('type', 'text').lower()
            if input_type not in ('hidden', 'submit', 'button', 'reset'):
                has_label = (self.in_label > 0 or
                             'aria-label' in attr_dict or
                             'aria-labelledby' in attr_dict or
                             'id' in attr_dict or
                             'placeholder' in attr_dict or
                             attr_dict.get('title'))
                if has_label:
                    self.passes.append(('form_label', f'Form control <{tag}> has accessible label or identifier.'))
                else:
                    self.violations.append(('form_label', f'Form control <{tag} name="{attr_dict.get("name", "")}"> is missing accessible label.'))

        elif tag == 'button':
            self.in_button = True
            self.current_button_text = ''
            self.current_button_attrs = attr_dict

    def handle_endtag(self, tag):
        if tag == 'label':
            self.in_label = max(0, self.in_label - 1)

        elif tag == 'title':

            self.in_title = False
            if self.title_text.strip():
                self.has_title = True
                self.passes.append(('page_title', '<title> element contains descriptive text.'))
            else:
                self.violations.append(('page_title', '<title> element is empty.'))

        elif tag == 'button':
            self.in_button = False
            has_name = (bool(self.current_button_text.strip()) or
                        'aria-label' in self.current_button_attrs or
                        'aria-labelledby' in self.current_button_attrs or
                        self.current_button_attrs.get('title'))
            if has_name:
                self.passes.append(('button_name', f'Button has accessible name: "{self.current_button_text.strip() or self.current_button_attrs.get("aria-label")}".'))
            else:
                self.violations.append(('button_name', 'Button is missing an accessible name or label.'))

    def handle_data(self, data):
        if self.in_title:
            self.title_text += data
        if self.in_button:
            self.current_button_text += data

    def finalize(self):
        if not self.has_main:
            self.violations.append(('landmarks', 'Page is missing a <main> or role="main" landmark region.'))
        else:
            self.passes.append(('landmarks', 'Page includes a <main> landmark region.'))

        if self.headings:
            if 1 not in self.headings:
                self.violations.append(('heading_hierarchy', 'Page is missing an <h1> top-level heading.'))
            else:
                self.passes.append(('heading_hierarchy', 'Page includes an <h1> top-level heading.'))

            # Check for skipped levels
            prev = self.headings[0]
            for curr in self.headings[1:]:
                if curr > prev + 1:
                    self.violations.append(('heading_hierarchy', f'Heading level skipped from h{prev} directly to h{curr}.'))
                    break
                prev = curr


def audit_html(html_str, url_label=''):
    parser = AccessibilityAuditor()
    parser.feed(html_str)
    parser.finalize()

    is_valid = len(parser.violations) == 0
    return {
        'url': url_label,
        'passed': is_valid,
        'violations_count': len(parser.violations),
        'passes_count': len(parser.passes),
        'violations': [{'rule': r, 'message': m} for r, m in parser.violations],
        'passes': [{'rule': r, 'message': m} for r, m in parser.passes]
    }


def audit_application_routes(client, student_login_fn=None):
    results = []

    # Unauthenticated routes
    public_urls = ['/login', '/register']
    for url in public_urls:
        resp = client.get(url)
        if resp.status_code == 200:
            res = audit_html(resp.data.decode('utf-8', errors='ignore'), url)
            results.append(res)

    # Authenticated routes
    if student_login_fn:
        student_login_fn(client)
        auth_urls = [
            '/dashboard',
            '/tasks',
            '/deadlines',
            '/notes',
            '/resources',
            '/announcements',
            '/notifications',
            '/profile'
        ]
        for url in auth_urls:
            resp = client.get(url)
            if resp.status_code == 200:
                res = audit_html(resp.data.decode('utf-8', errors='ignore'), url)
                results.append(res)

    total_violations = sum(r['violations_count'] for r in results)
    total_passes = sum(r['passes_count'] for r in results)
    overall_passed = total_violations == 0

    return {
        'overall_passed': overall_passed,
        'total_violations': total_violations,
        'total_passes': total_passes,
        'routes_audited': len(results),
        'results': results
    }
