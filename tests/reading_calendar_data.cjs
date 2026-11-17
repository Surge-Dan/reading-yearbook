const assert=require('assert/strict'),fs=require('fs'),vm=require('vm'),path=require('path');
const context={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reading-yearbook-skill/assets/reading-share-art.js'),'utf8'),context);
const calendar=context.window.ReadingShareArtwork.calendarData;
for(const zone of ['Asia/Shanghai','America/Los_Angeles','UTC']){
 process.env.TZ=zone;
 const data={year:2026,as_of:'2026-01-06',features:{daily:{'2026-01-01':0,'2026-01-02':900,'2026-01-03':1800,'2026-01-04':3600,'2026-01-05':3601,'2026-01-07':100,'2025-12-31':60}}};
 const model=calendar(data);assert.equal(model.cells.length,365);assert.equal(model.cells[0].date,'2026-01-01');assert.equal(model.cells.at(-1).date,'2026-12-31');
 assert.equal(model.cells[0].row,3);assert.equal(model.cells[0].state,'zero');assert.equal(model.observed,5);
 assert.deepEqual(Array.from(model.cells.slice(1,5),x=>x.level),[1,2,3,4]);assert.equal(model.cells[5].state,'missing');assert.equal(model.cells[6].state,'future');assert.equal(model.cells[6].seconds,null);
 const leap=calendar({year:2024,as_of:'2024-12-31'});assert.equal(leap.cells.length,366);assert(leap.cells.some(x=>x.date==='2024-02-29'));
 const wide=calendar({year:2012});assert.equal(wide.weeks,54);
 assert.equal(calendar({year:'2026'}).cells.length,365);assert.throws(()=>calendar({year:'not-a-year'}));assert.throws(()=>calendar({year:2201}));
 const none=calendar({year:2026,as_of:'2026-03-01'});assert.equal(none.observed,0);assert.equal(none.cells.filter(x=>x.state==='missing').length,60);
 const invalid=calendar({year:2026,as_of:'2026-01-02',features:{daily:{'2026-01-01':-1,'2026-01-02':false}}});assert.equal(invalid.observed,0);
}
console.log('PASS: 365/366 days, Monday alignment, 54-week year, timezone independence, cutoff, intensity, zero/missing/future and invalid data.');
