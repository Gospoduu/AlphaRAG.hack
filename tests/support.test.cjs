const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../Back/static/index.html'), 'utf8');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    innerHTML: '', value: '', textContent: '', scrollTop: 0, scrollHeight: 100,
    classList: {add() {}, remove() {}, toggle() {}},
    appendChild() {}, setAttribute() {}, focus() {},
    insertAdjacentHTML(_, content) { this.innerHTML += content; },
    querySelector: () => element('button'), form: {querySelector: () => element('submit')}
  });
  return elements.get(id);
}
const context = vm.createContext({
  assert, console: {warn() {}, log() {}}, Date, Map,
  location: {protocol: 'http:', hostname: 'localhost'}, window: {},
  WebSocket: {OPEN: 1},
  localStorage: {getItem() {return null;}, setItem() {}},
  document: {
    addEventListener() {}, getElementById: element,
    createElement: () => element(Symbol()), querySelector: () => element('nav'), querySelectorAll: () => []
  }
});
for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) vm.runInContext(script, context);
assert(!html.includes('showSupportRequest'));
assert(!html.includes("sendSupportEvent('SUPPORT_REQUEST'"));
(async () => {
  await vm.runInContext(`(async () => {
    userUuid = 'user-a';
    const sent = [];
    socket = {readyState: 1, send(raw) {sent.push(JSON.parse(raw));}};
    fetch = async () => ({ok:true, json:async () => ({items:[], total:0})});
    supportState('a').problem = 'Первичное обращение';
    await selectSupportDialog('a');
    assert.equal(document.getElementById('supportStatus').textContent, 'Ожидает');
    assert.match(document.getElementById('supportMessages').innerHTML, /support-typing/);
    handleSupportEvent('update_dialog_status', {support_dialog_id:'a', new_status:'IN_PROGRESS'});
    assert.equal(document.getElementById('supportStatus').textContent, 'В работе');
    handleSupportEvent('support_message', {support_dialog_id:'a', text:'Ответ'});
    assert.equal(document.getElementById('supportStatus').textContent, 'Обработан');
    assert.doesNotMatch(document.getElementById('supportMessages').innerHTML, /support-typing/);
    document.getElementById('supportInput').value = 'Уточнение';
    sendSupportMessage({preventDefault() {}});
    assert.equal(sent[0].event, 'SUPPORT_MESSAGE');
    assert.equal(supportState('a').status, 'waiting');
    assert.match(document.getElementById('supportMessages').innerHTML, /typing-cursor/);
    await selectSupportDialog('b');
    handleSupportEvent('support_message', {support_dialog_id:'a', text:'Второй ответ'});
    assert.equal(supportState('a').status, 'complete');
    assert.equal(supportState('a').unread, 1);
    await selectSupportDialog('a');
    assert.equal(supportState('a').messages.length, 3);
    assert.equal(document.getElementById('supportStatus').textContent, 'Обработан');

    // An older REST snapshot must not overwrite the latest WS status.
    fetch = async url => ({ok:true, json:async () => url.includes('/supporters/') ? {line:2} : [{id:'a', status:'in_progress'}]});
    await fetchSupportDialogs();
    assert.equal(supportState('a').status, 'complete');
    supportState('a').statusDirty = false;
    await fetchSupportDialogs();
    assert.equal(supportState('a').status, 'in_progress');

    // History is lazy, paginated, user-scoped, escaped, and cached per dialog.
    bindSupportSource(supportState('a'), 7);
    let calls = 0;
    fetch = async url => {
      calls++;
      assert(url.includes('/api/chat/7/messages?'));
      assert(!url.includes('/chats'));
      const firstPage = url.includes('start_message_idx=0&');
      const messages = firstPage ? Array.from({length:50},(_,i)=>({local_id:51-i,text:'m'+(51-i),user_role:'bot'})) : [{local_id:1,text:'<script>unsafe</script>',user_role:'user'}];
      return {ok:true,json:async()=>({status:'ok',messages})};
    };
    assert.equal(calls, 0);
    await toggleSupportBotHistory();
    assert.equal(calls, 2);
    assert.equal(supportState('a').botHistory[0].messages.length, 51);
    assert.equal(supportState('a').botHistory[0].messages[0].local_id, 1);
    assert.match(document.getElementById('supportMessages').innerHTML, /&lt;script&gt;/);
    await toggleSupportBotHistory(); await toggleSupportBotHistory();
    assert.equal(calls, 2);
    supportState('a').botHistory = null;
    fetch = async () => {throw Error('offline');};
    await loadSupportBotHistory();
    assert.match(document.getElementById('supportMessages').innerHTML, /Повторить загрузку/);

    // Loading another ticket's history must not replace the current view.
    let release;
    fetch = async url => {
      if (url.includes('/chat/7/messages')) await new Promise(resolve => {release = resolve;});
      return {ok:true,json:async()=>({status:'ok', messages:[], items:[], total:0})};
    };
    const loading = loadSupportBotHistory();
    await selectSupportDialog('b');
    const before = document.getElementById('supportMessages').innerHTML;
    release(); await loading;
    assert.equal(document.getElementById('supportMessages').innerHTML, before);
    handleSupportEvent('user_feedback_request', {support_dialog_id:'b'});
    assert.equal(document.getElementById('supportStatus').textContent, 'Закрыт');
    assert.doesNotMatch(document.getElementById('supportMessages').innerHTML, /support-typing/);
    // Legacy tickets request a source choice instead of fetching unrelated chats.
    await selectSupportDialog('legacy');
    supportState('legacy').historyOpen = true;
    let unexpected = 0;
    fetch = async () => {unexpected++; throw Error('Unexpected request');};
    await loadSupportBotHistory();
    assert.equal(unexpected, 0);
    assert.match(renderSupportBotHistory(supportState('legacy')), /Исходный чат с ботом/);
    resetSupportState();
    assert.equal(supportStates.size, 0);
  })()`, context);
  console.log('PASS: status lifecycle, typing indicator, background replies, REST restore, history pagination/cache/escaping/errors/isolation, closure, reset');
})().catch(error => {console.error(error); process.exitCode = 1;});
