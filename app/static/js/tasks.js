const taskList=document.getElementById('taskList');
let selectedIds=new Set();

function updateBulkBar(){
  const bar=document.getElementById('bulkBar');
  const count=selectedIds.size;
  if(count>0){
    bar.style.display='flex';
    document.getElementById('bulkCount').textContent=count+' selected';
  } else {
    bar.style.display='none';
  }
  // Sync select-all checkbox state
  const allCbs=document.querySelectorAll('.task-cb');
  const selectAll=document.getElementById('selectAllTasks');
  if(selectAll){
    selectAll.checked=allCbs.length>0&&[...allCbs].every(cb=>cb.checked);
    selectAll.indeterminate=count>0&&count<allCbs.length;
  }
}

function toggleSelect(id,checked){
  if(checked) selectedIds.add(id); else selectedIds.delete(id);
  updateBulkBar();
}

function toggleSelectAll(checked){
  document.querySelectorAll('.task-cb').forEach(cb=>{
    cb.checked=checked;
    const id=parseInt(cb.dataset.id);
    if(checked) selectedIds.add(id); else selectedIds.delete(id);
  });
  updateBulkBar();
}

async function bulkAction(action){
  const ids=[...selectedIds];
  if(!ids.length) return;
  if(action==='delete_all'&&!confirm(`Delete ${ids.length} task(s)? This cannot be undone.`)) return;
  try{
    const res=await api('/api/tasks/bulk',{method:'POST',body:JSON.stringify({action,ids})});
    const verb=action==='delete_all'?'deleted':action==='complete_all'?'marked complete':'marked pending';
    toast(`${res.affected} task(s) ${verb}`);
    selectedIds.clear();
    loadTasks();
  }catch(e){toast(e.message,'error')}
}

async function loadTasks(){
  try{
    const p=new URLSearchParams({search:document.getElementById('taskSearch').value,status:document.getElementById('taskStatus').value,priority:document.getElementById('taskPriority').value,category:document.getElementById('taskCategory').value});
    const tasks=await api('/api/tasks?'+p);
    // Keep only IDs that still exist
    const existingIds=new Set(tasks.map(t=>t.id));
    for(const id of selectedIds) if(!existingIds.has(id)) selectedIds.delete(id);
    if(tasks.length){
      taskList.innerHTML=`<table><thead><tr>
<th><input type="checkbox" id="selectAllTasks" title="Select all" onchange="toggleSelectAll(this.checked)"></th>
<th>Task</th><th>Category</th><th>Due</th><th>Priority</th><th>Status</th><th></th></tr></thead>
<tbody>${tasks.map(t=>`<tr>
<td><input type="checkbox" class="task-cb" data-id="${t.id}" ${selectedIds.has(t.id)?'checked':''} onchange="toggleSelect(${t.id},this.checked)"></td>
<td><strong>${esc(t.title)}</strong><small>${esc(t.description||'')}</small></td>
<td>${t.category}</td><td>${t.due_date||'—'}</td>
<td><span class="badge ${t.priority}">${t.priority}</span></td>
<td><button class="status-btn ${t.completed?'done':''}" onclick="toggleTask(${t.id},${!t.completed})">${t.completed?'Completed':'Pending'}</button></td>
<td><button class="icon-btn" title="Copy task details" onclick='copyTaskDetails(${JSON.stringify(t)})'>📋</button> <button class="icon-btn" onclick='editTask(${JSON.stringify(t)})'>✎</button> <button class="icon-btn" onclick="deleteTask(${t.id})">🗑</button></td>
</tr>`).join('')}</tbody></table>`;
    } else {
      taskList.innerHTML='<div class="empty">No tasks match your filters.</div>';
    }
    updateBulkBar();
  }catch(e){taskList.innerHTML=`<div class="empty">${esc(e.message)}</div>`}
}

async function copyTaskDetails(t){const text=t.due_date?`${t.title} (Due: ${t.due_date})`:t.title;try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(text)}else{const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove()}toast('Task details copied to clipboard')}catch(e){toast('Failed to copy task details','error')}}
async function toggleTask(id,completed){try{await api('/api/tasks/'+id,{method:'PUT',body:JSON.stringify({completed})});loadTasks()}catch(e){toast(e.message,'error')}}
async function deleteTask(id){if(!confirm('Delete this task?'))return;try{await api('/api/tasks/'+id,{method:'DELETE'});toast('Task deleted');loadTasks()}catch(e){toast(e.message,'error')}}
function editTask(t){const f=document.getElementById('taskForm');f.id.value=t.id;f.title.value=t.title;f.description.value=t.description||'';f.priority.value=t.priority;f.category.value=t.category;f.due_date.value=t.due_date||'';document.getElementById('taskModalTitle').textContent='Edit task';openModal('task-modal')}
document.getElementById('taskForm').addEventListener('submit',async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target)),id=d.id;delete d.id;try{await api(id?'/api/tasks/'+id:'/api/tasks',{method:id?'PUT':'POST',body:JSON.stringify(d)});closeModal('task-modal');e.target.reset();document.getElementById('taskModalTitle').textContent='New task';toast(id?'Task updated':'Task created');loadTasks()}catch(err){toast(err.message,'error')}})
['taskSearch','taskStatus','taskPriority','taskCategory'].forEach(id=>document.getElementById(id).addEventListener('input',loadTasks));
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))} loadTasks();
