// alerts.js rules, run in node (no browser): an id is announced once, a video chimes once when Kiro finishes it.
import fs from 'fs';
import assert from 'assert';
const m={};new Function('module',fs.readFileSync(new URL('../plugins/kirocut/lib/kirocut/alerts.js',import.meta.url),'utf8'))(m);
const {firstTime,finished}=m.exports;
// the same id after a reload or in a second tab: no second chime
let seen=firstTime([],'q1');assert.deepEqual(seen,['q1']);
assert.equal(firstTime(seen,'q1'),null);
assert.deepEqual(firstTime(seen,'q2'),['q2','q1']);
assert.equal(firstTime(Array.from({length:40},(_,i)=>'x'+i),'q').length,30,'the list stays short');
// a draft finishes: cutting -> cut chimes, a new or unchanged video does not
let r=finished({a:'cutting',b:'cut'},{a:'cut',b:'cut',c:'cutting'});
assert.deepEqual(r.done,['a']);assert.deepEqual(r.next,{a:'cut',b:'cut',c:'cutting'});
// the notes go round: working, then the next draft is ready
r=finished({a:'notes'},{a:'rendering'});assert.deepEqual(r.done,[]);
r=finished(r.next,{a:'done'});assert.deepEqual(r.done,['a']);
console.log('alerts ok');
