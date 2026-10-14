from flask import session, request, has_request_context
from flask_login import current_user

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'hi': 'हिन्दी'
}

DEFAULT_LANGUAGE = 'en'

TRANSLATIONS = {
    'en': {
        'nav_dashboard': 'Dashboard',
        'nav_tasks': 'Tasks',
        'nav_deadlines': 'Deadlines',
        'nav_notes': 'Notes',
        'nav_resources': 'Resources',
        'nav_announcements': 'Announcements',
        'nav_notifications': 'Notifications',
        'nav_profile': 'Profile',
        'nav_admin': 'Admin',
        'logout': 'Logout',
        'login': 'Login',
        'register': 'Register',
        'save': 'Save',
        'delete': 'Delete',
        'edit': 'Edit',
        'cancel': 'Cancel',
        'search': 'Search',
        'completed': 'Completed',
        'pending': 'Pending',
        'overdue': 'Overdue',
        'today': 'Today',
        'upcoming': 'Upcoming',
        'all_caught_up': 'You’re all caught up.',
        'no_tasks': 'No tasks match your filters.',
        'no_notes': 'No notes yet.',
        'no_resources': 'No resources yet.',
        'no_announcements': 'No announcements yet.',
        'profile_updated': 'Profile updated.',
        'language_updated': 'Language preference updated.'
    },
    'es': {
        'nav_dashboard': 'Panel Principal',
        'nav_tasks': 'Tareas',
        'nav_deadlines': 'Fechas Límite',
        'nav_notes': 'Notas',
        'nav_resources': 'Recursos',
        'nav_announcements': 'Anuncios',
        'nav_notifications': 'Notificaciones',
        'nav_profile': 'Perfil',
        'nav_admin': 'Administración',
        'logout': 'Cerrar Sesión',
        'login': 'Iniciar Sesión',
        'register': 'Registrarse',
        'save': 'Guardar',
        'delete': 'Eliminar',
        'edit': 'Editar',
        'cancel': 'Cancelar',
        'search': 'Buscar',
        'completed': 'Completada',
        'pending': 'Pendiente',
        'overdue': 'Atrasada',
        'today': 'Hoy',
        'upcoming': 'Próximamente',
        'all_caught_up': 'Estás al día.',
        'no_tasks': 'No hay tareas que coincidan.',
        'no_notes': 'Sin notas aún.',
        'no_resources': 'Sin recursos aún.',
        'no_announcements': 'Sin anuncios aún.',
        'profile_updated': 'Perfil actualizado.',
        'language_updated': 'Preferencia de idioma actualizada.'
    },
    'fr': {
        'nav_dashboard': 'Tableau de bord',
        'nav_tasks': 'Tâches',
        'nav_deadlines': 'Échéances',
        'nav_notes': 'Notes',
        'nav_resources': 'Ressources',
        'nav_announcements': 'Annonces',
        'nav_notifications': 'Notifications',
        'nav_profile': 'Profil',
        'nav_admin': 'Admin',
        'logout': 'Déconnexion',
        'login': 'Connexion',
        'register': "S'inscrire",
        'save': 'Enregistrer',
        'delete': 'Supprimer',
        'edit': 'Modifier',
        'cancel': 'Annuler',
        'search': 'Rechercher',
        'completed': 'Terminé',
        'pending': 'En attente',
        'overdue': 'En retard',
        'today': "Aujourd'hui",
        'upcoming': 'À venir',
        'all_caught_up': 'Vous êtes à jour.',
        'no_tasks': 'Aucune tâche correspondante.',
        'no_notes': 'Aucune note pour le moment.',
        'no_resources': 'Aucune ressource pour le moment.',
        'no_announcements': 'Aucune annonce pour le moment.',
        'profile_updated': 'Profil mis à jour.',
        'language_updated': 'Préférence linguistique mise à jour.'
    },
    'de': {
        'nav_dashboard': 'Übersicht',
        'nav_tasks': 'Aufgaben',
        'nav_deadlines': 'Fristen',
        'nav_notes': 'Notizen',
        'nav_resources': 'Ressourcen',
        'nav_announcements': 'Ankündigungen',
        'nav_notifications': 'Benachrichtigungen',
        'nav_profile': 'Profil',
        'nav_admin': 'Admin',
        'logout': 'Abmelden',
        'login': 'Anmelden',
        'register': 'Registrieren',
        'save': 'Speichern',
        'delete': 'Löschen',
        'edit': 'Bearbeiten',
        'cancel': 'Abbrechen',
        'search': 'Suchen',
        'completed': 'Erledigt',
        'pending': 'Ausstehend',
        'overdue': 'Überfällig',
        'today': 'Heute',
        'upcoming': 'Bevorstehend',
        'all_caught_up': 'Alles erledigt.',
        'no_tasks': 'Keine passenden Aufgaben.',
        'no_notes': 'Noch keine Notizen.',
        'no_resources': 'Noch keine Ressourcen.',
        'no_announcements': 'Noch keine Ankündigungen.',
        'profile_updated': 'Profil aktualisiert.',
        'language_updated': 'Spracheinstellung aktualisiert.'
    },
    'hi': {
        'nav_dashboard': 'डैशबोर्ड',
        'nav_tasks': 'कार्य',
        'nav_deadlines': 'समय सीमा',
        'nav_notes': 'नोट्स',
        'nav_resources': 'संसाधन',
        'nav_announcements': 'घोषणाएँ',
        'nav_notifications': 'सूचनाएं',
        'nav_profile': 'प्रोफ़ाइल',
        'nav_admin': 'व्यवस्थापक',
        'logout': 'लॉग आउट',
        'login': 'लॉग इन',
        'register': 'पंजीकरण',
        'save': 'सहेजें',
        'delete': 'हटाएं',
        'edit': 'संपादित करें',
        'cancel': 'रद्द करें',
        'search': 'खोजें',
        'completed': 'पूर्ण',
        'pending': 'लंबित',
        'overdue': 'अतिदेय',
        'today': 'आज',
        'upcoming': 'आगामी',
        'all_caught_up': 'सब कुछ अद्यतित है।',
        'no_tasks': 'कोई कार्य नहीं मिला।',
        'no_notes': 'अभी तक कोई नोट नहीं है।',
        'no_resources': 'अभी कोई संसाधन नहीं है।',
        'no_announcements': 'अभी कोई घोषणा नहीं है।',
        'profile_updated': 'प्रोफ़ाइल अपडेट की गई।',
        'language_updated': 'भाषा प्राथमिकता अपडेट की गई।'
    }
}


def get_current_language():
    if not has_request_context():
        return DEFAULT_LANGUAGE

    # 1. Check query parameter
    lang = request.args.get('lang')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # 2. Check session
    if 'lang' in session and session['lang'] in SUPPORTED_LANGUAGES:
        return session['lang']

    # 3. Check authenticated user's setting
    if current_user and current_user.is_authenticated and hasattr(current_user, 'language'):
        if current_user.language and current_user.language in SUPPORTED_LANGUAGES:
            return current_user.language

    # 4. Check Accept-Language header
    if request.accept_languages:
        match = request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys())
        if match:
            return match

    return DEFAULT_LANGUAGE


def translate(key, default=None, lang=None, **kwargs):
    if not lang:
        lang = get_current_language()

    catalog = TRANSLATIONS.get(lang, {})
    text = catalog.get(key)
    if text is None:
        # Fall back to English
        text = TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key)
    if text is None:
        text = default if default is not None else key

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def get_translations_for_client(lang=None):
    if not lang:
        lang = get_current_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
