const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../Back/static/index.html'), 'utf8');
const code = html.slice(html.indexOf('    function reactionButtons('), html.indexOf('    function copyText('));
const notice = {textContent: ''};
const parent = {dataset: {}, querySelector: () => notice, querySelectorAll: () => buttons};
const buttons = ['1', '-1'].map(value => ({
  dataset: {messageId:'123', reaction:value}, parentElement: parent, pressed:'false',
  getAttribute() {return this.pressed;}, setAttribute(_,value) {this.pressed=value;},
  classList: {toggle() {}}
}));
const context = vm.createContext({getApiBase:()=> 'http://localhost:8000'});
vm.runInContext(code, context);
assert.match(context.reactionButtons(123, 1), /active-like/);
assert.match(context.reactionButtons(123, -1), /active-dislike/);
assert.match(context.reactionButtons(undefined), /disabled/);
(async () => {
  const requests = [];
  let release;
  context.fetch = async (url, options) => {
    assert.equal(url, 'http://localhost:8000/api/chat/reaction');
    assert.equal(options.method, 'PATCH');
    const data = JSON.parse(options.body);
    requests.push(data);
    if (requests.length === 1) await new Promise(resolve => {release = resolve;});
    return {ok:true, json:async()=>({status:'ok',...data})};
  };
  const first = context.toggleFb(buttons[0]);
  await context.toggleFb(buttons[1]); // Ignore duplicate clicks during save.
  assert.equal(requests.length, 1);
  release(); await first;
  assert.equal(buttons[0].pressed, 'true');
  await context.toggleFb(buttons[1]);
  assert.equal(buttons[0].pressed, 'false');
  assert.equal(buttons[1].pressed, 'true');
  await context.toggleFb(buttons[1]);
  assert.equal(buttons[1].pressed, 'false');
  assert.deepEqual(requests, [
    {message_id:123, reaction:1}, {message_id:123, reaction:-1}, {message_id:123, reaction:0}
  ]);
  context.fetch = async () => ({ok:false, status:500});
  await context.toggleFb(buttons[0]);
  assert.equal(buttons[0].pressed, 'false');
  assert.match(notice.textContent, /Не удалось сохранить/);
  assert.equal(buttons[0].disabled, false);
  console.log('PASS: PATCH message ID, like/dislike/reset, saved rendering, duplicate clicks, failure recovery');
})().catch(error=>{console.error(error); process.exitCode=1;});
