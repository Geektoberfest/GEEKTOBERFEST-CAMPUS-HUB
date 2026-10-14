from tests.conftest import login

def test_notes_crud(client,student):
    login(client);r=client.post('/api/notes',json={'title':'CN','content':'OSI layers','subject':'CN'});assert r.status_code==201;n=r.get_json()['data'];nid=n['id']
    assert client.put(f'/api/notes/{nid}',json={'title':'CN Updated','content':'TCP UDP','subject':'CN'}).status_code==200
    assert client.get('/api/notes').status_code==200
    assert client.delete(f'/api/notes/{nid}').status_code==200

def test_note_markdown_export(client,student,admin):
    login(client)
    r = client.post('/api/notes', json={'title':'Distributed Systems Note','content':'Consensus, Paxos, Raft','subject':'Distributed Systems'})
    assert r.status_code == 201
    nid = r.get_json()['data']['id']

    # Export note
    res = client.get(f'/notes/{nid}/export')
    assert res.status_code == 200
    assert 'text/markdown' in res.content_type
    assert 'attachment; filename="Distributed_Systems_Note.md"' in res.headers.get('Content-Disposition', '')
    assert b'# Distributed Systems Note' in res.data
    assert b'Consensus, Paxos, Raft' in res.data

    # Page renders export link
    page_res = client.get('/notes')
    assert page_res.status_code == 200
    assert f'/notes/{nid}/export'.encode() in page_res.data

    # Another user cannot export this note (scoping)
    client.post('/logout')
    login(client, 'admin@test.local')
    assert client.get(f'/notes/{nid}/export').status_code == 404

def test_notes_page_and_char_counter(client,student):
    login(client)
    res = client.get('/notes')
    assert res.status_code == 200
    assert b'noteCharCount' in res.data
    assert b'characters remaining' in res.data
    js_res = client.get('/static/js/notes.js')
    assert js_res.status_code == 200
    assert b'updateNoteCharCount' in js_res.data
