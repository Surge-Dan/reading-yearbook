/* Local editing references, separate from reading materials and presentation. */
window.ReadingShareState = (() => {
  'use strict';
  function fingerprint(value){
    let a=2166136261,b=5381;
    for(let i=0;i<value.length;i++){a=Math.imul(a^value.charCodeAt(i),16777619);b=Math.imul(b,33)^value.charCodeAt(i);}
    return (a>>>0).toString(16)+':'+(b>>>0).toString(16)+':'+value.length;
  }
  function candidates(page){
    return [
      ...page.book.highlights.map(n=>({kind:'highlight',id:n.source_id||'',text:n.text})),
      ...page.book.thoughts.flatMap(n=>[
        {kind:'thought',id:n.source_id||'',text:n.text},
        ...(n.quote?[{kind:'thought-quote',id:n.source_id||'',text:n.quote}]:[])
      ])
    ];
  }
  function create({data,pages,state,notice=()=>{}}){
    const key=/^[a-f0-9]{32}$/.test(data.edit_scope||'')?
      `reading-yearbook:share:v1:${data.edit_scope}:${data.year}`:null;
    let storage=null;
    function restore(){
      if(!key)return false;
      let saved;
      try{storage=window.localStorage;saved=JSON.parse(storage.getItem(key)||'null');}
      catch{return false;}
      if(!saved||saved.version!==1||!Array.isArray(saved.known)||!saved.known.length||!Array.isArray(saved.selected))return false;
      if(!saved.known.every(id=>typeof id==='string')||!saved.selected.every(id=>typeof id==='string'))return false;
      const valid=new Set(pages.map(p=>p.id)),known=new Set(saved.known),selected=new Set(saved.selected);
      if(saved.selected.some(id=>!known.has(id)))return false;
      state.selection=new Set(saved.selected.filter(id=>valid.has(id)));
      if(saved.known.every(id=>selected.has(id)))for(const id of valid)if(!known.has(id))state.selection.add(id);
      if(['3:4','1:1','4:5'].includes(saved.ratio))state.ratio=saved.ratio;
      if(valid.has(saved.preview))state.preview=saved.preview;
      let invalid=0;
      for(const p of pages.filter(p=>p.kind==='book')){
        const ref=saved.materials?.[p.id];if(!ref)continue;
        const row=candidates(p).find(n=>n.kind===ref.kind&&(!ref.id||n.id===ref.id)&&fingerprint(n.text)===ref.fingerprint);
        if(row){p.quote=row.text;p.textKind=row.kind==='thought'?'thought':'highlight';}else invalid++;
      }
      if(invalid)notice(`${invalid}本书的原选句已变更，已换成现有材料；导出前再看一眼。`);
      return true;
    }
    function save(){
      if(!storage||!key)return;
      const materials=Object.fromEntries(pages.filter(p=>p.kind==='book').map(p=>{
        const row=candidates(p).find(n=>n.text===p.quote&&(p.textKind==='thought'?n.kind==='thought':n.kind!=='thought'));
        return [p.id,row?{kind:row.kind,id:row.id,fingerprint:fingerprint(row.text)}:null];
      }));
      try{storage.setItem(key,JSON.stringify({version:1,ratio:state.ratio,preview:state.preview,
        known:pages.map(p=>p.id),selected:[...state.selection],materials}));}
      catch{storage=null;notice('浏览器未能保存这次选择，当前仍可正常导出。');}
    }
    return {restore,save};
  }
  return {create};
})();
