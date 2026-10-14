let lastActiveElement = null;

function openModal(id){
    const el = document.getElementById(id);
    if (!el) return;
    lastActiveElement = document.activeElement;
    el.classList.add('show');
    el.setAttribute('aria-hidden', 'false');
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    const focusable = el.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length) {
        setTimeout(() => focusable[0].focus(), 50);
    }
}

function closeModal(id){
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('show');
    el.setAttribute('aria-hidden', 'true');
    if (lastActiveElement && typeof lastActiveElement.focus === 'function') {
        lastActiveElement.focus();
    }
}

window.addEventListener('click', e => {
    if (e.target.classList.contains('modal')) closeModal(e.target.id);
});

window.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.show').forEach(m => closeModal(m.id));
    }
});

function toast(message, type='success'){
    const el = document.createElement('div');
    el.className = 'flash ' + type;
    el.setAttribute('role', 'alert');
    el.textContent = message;
    document.querySelector('.flash-stack')?.append(el) || document.body.prepend(Object.assign(document.createElement('div'), {className: 'flash-stack'}));
    const box = document.querySelector('.flash-stack');
    if (!box.contains(el)) box.append(el);
    setTimeout(() => el.remove(), 3000);
}

async function api(url, options={}){
    const opts = {...options, headers: {'Content-Type': 'application/json', ...(options.headers || {})}};
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    if (token) opts.headers['X-CSRFToken'] = token;
    const r = await fetch(url, opts);
    const data = await r.json().catch(() => ({success: false, error: 'Invalid server response'}));
    if (!r.ok || data.success === false) throw new Error(data.error || 'Request failed');
    return data.data;
}

const btt=document.getElementById('backToTop');if(btt){window.addEventListener('scroll',()=>{if(window.scrollY>200){btt.classList.add('visible')}else{btt.classList.remove('visible')}});btt.addEventListener('click',()=>{window.scrollTo({top:0,behavior:'smooth'});const target=document.querySelector('.topbar a.brand')||document.querySelector('h1')||document.body;if(target){if(!target.hasAttribute('tabindex'))target.setAttribute('tabindex','-1');target.focus({preventScroll:true})}})}

function confirmDialog(options={}){
    return new Promise(resolve=>{
        const modal=document.getElementById('confirmModal');
        if(!modal){resolve(window.confirm(options.message||'Are you sure?'));return}
        const titleEl=document.getElementById('confirmModalTitle');
        const msgEl=document.getElementById('confirmModalMessage');
        const confirmBtn=document.getElementById('confirmModalConfirm');
        const cancelBtn=document.getElementById('confirmModalCancel');
        const closeBtn=document.getElementById('confirmModalClose');

        if(titleEl)titleEl.textContent=options.title||'Confirm action';
        if(msgEl)msgEl.textContent=options.message||'Are you sure? This action cannot be undone.';
        if(confirmBtn){
            confirmBtn.textContent=options.confirmText||'Confirm';
            confirmBtn.className='btn '+(options.danger!==false?'danger':'primary');
        }
        if(cancelBtn)cancelBtn.textContent=options.cancelText||'Cancel';

        modal.classList.add('show');
        confirmBtn?.focus();

        function cleanup(result){
            modal.classList.remove('show');
            confirmBtn?.removeEventListener('click',onConfirm);
            cancelBtn?.removeEventListener('click',onCancel);
            closeBtn?.removeEventListener('click',onCancel);
            document.removeEventListener('keydown',onKeyDown);
            resolve(result);
        }
        function onConfirm(){cleanup(true)}
        function onCancel(){cleanup(false)}
        function onKeyDown(e){if(e.key==='Escape'){e.preventDefault();cleanup(false)}}

        confirmBtn?.addEventListener('click',onConfirm);
        cancelBtn?.addEventListener('click',onCancel);
        closeBtn?.addEventListener('click',onCancel);
        document.addEventListener('keydown',onKeyDown);
    });
}

document.addEventListener('submit',async e=>{
    const form=e.target;
    const msg=form.getAttribute('data-confirm');
    if(msg&&!form.dataset.confirmed){
        e.preventDefault();
        const ok=await confirmDialog({
            title:form.getAttribute('data-confirm-title')||'Confirm action',
            message:msg,
            confirmText:form.getAttribute('data-confirm-btn')||'Delete',
            danger:true
        });
        if(ok){
            form.dataset.confirmed='true';
            form.submit();
        }
    }
});
