(async page => {
  const live=page.locator("lx-music-card").first();
  await live.waitFor();
  await live.evaluate(real => {
    const preview=document.createElement("lx-music-card");
    preview.id="lx-card-ui-check";
    preview.style.cssText="position:fixed;top:0;left:0;width:380px;max-height:95vh;overflow:auto;z-index:99999";
    preview.setConfig({type:"custom:lx-music-card",entity:real.playerEntity()});
    const calls=[],wsCalls=[],queue=[],tracks=new Map();
    preview.hass={...real.hass,callService:async(...args)=>{calls.push(args);return [];},callWS:async msg=>{
      wsCalls.push(msg);
      if(msg.action==="play")throw new Error("Playback is forbidden in browser verification");
      if(msg.action==="enqueue") {const batch=msg.track_ids.map(id=>tracks.get(id));if(batch.some(s=>!s))throw new Error("Unknown track reference");queue.push(...batch);return {queued:batch.length};}
      const result=await real.hass.callWS(msg);
      if(msg.action==="status")return {...result,upcoming:[...queue]};
      if(Array.isArray(result))for(const item of result)if(item.track_id)tracks.set(item.track_id,item);
      return result;
    }};
    document.body.append(preview);
    window.__lxCardCheck={preview,calls,wsCalls,queue,original:real.hass};
  });
  const fixture=page.locator("#lx-card-ui-check");
  const ready=()=>page.waitForFunction(()=>window.__lxCardCheck.preview.data&&!window.__lxCardCheck.preview.busy);
  try {
    await ready();
    for(const name of ["Previous track","Play","Next track","Stop","Mute"]) {
      await fixture.getByRole("button",{name,exact:true}).click();
      await ready();
    }
    await fixture.getByRole("slider",{name:"Volume",exact:true}).evaluate(input=>{
      input.value="0.42";input.dispatchEvent(new Event("change",{bubbles:true}));
    });
    await ready();
    const output=await fixture.getByRole("combobox",{name:"Cast target"}).evaluate(select=>[...select.options].find(o=>o.value&&o.value!==select.value)?.value);
    if(output) {await fixture.getByRole("combobox",{name:"Cast target"}).selectOption(output);await ready();}
    await fixture.evaluate(card=>{
      const entity=card.playerEntity();const state=card.hass.states[entity];
      card._hass={...card.hass,states:{...card.hass.states,[entity]:{...state,state:"playing",last_updated:"test-playing",attributes:{...state.attributes,media_duration:180,media_position:20}}}};
      card.updatePlayer();
    });
    await fixture.getByRole("button",{name:"Pause",exact:true}).click();await ready();
    await fixture.getByRole("slider",{name:"Playback position",exact:true}).evaluate(input=>{
      input.value="60";input.dispatchEvent(new Event("change",{bubbles:true}));
    });
    await ready();
    const calls=await page.evaluate(()=>window.__lxCardCheck.calls);
    const expected=["media_previous_track","media_play","media_next_track","media_stop","volume_mute","volume_set",...(output?["select_source"]:[]),"media_pause","media_seek"];
    if(JSON.stringify(calls.map(c=>c[1]))!==JSON.stringify(expected))throw new Error("Incorrect service routing");
    if(calls.some(c=>c[2].entity_id!=="media_player.lx_server"))throw new Error("Controls bypassed LX Server player");
    await fixture.getByRole("tab",{name:"Browse",exact:true}).click();
    await fixture.getByRole("textbox",{name:"Search music"}).fill("Mozart");
    await fixture.getByRole("button",{name:"Search",exact:true}).click();
    await ready();
    const results=await fixture.getByRole("button",{name:"Play track",exact:true}).count();
    if(!results)throw new Error("Search returned no visible tracks");
    await fixture.getByRole("button",{name:"Add track to queue",exact:true}).first().click();await ready();
    await fixture.getByRole("status").filter({hasText:"Added 1 track to queue"}).waitFor();
    await fixture.getByRole("button",{name:"Add all results to queue",exact:true}).click();await ready();
    const queueAfterSongs=await page.evaluate(()=>window.__lxCardCheck.queue.length);
    if(queueAfterSongs!==results+1)throw new Error("Song enqueue did not append all results");
    await fixture.getByRole("button",{name:"Artists",exact:true}).click();
    const artistSources=await fixture.getByRole("combobox",{name:"Music source"}).evaluate(s=>[...s.options].map(o=>o.value));
    if(JSON.stringify(artistSources)!==JSON.stringify(["wy","tx"]))throw new Error("Unsupported artist sources shown");
    await fixture.getByRole("button",{name:"Search",exact:true}).click();await ready();
    const artists=await fixture.getByRole("button",{name:"Open artist",exact:true}).count();
    if(artists<2)throw new Error("Artist search failed");
    await fixture.getByRole("button",{name:"Open artist",exact:true}).nth(1).click();await ready();
    const artistTracks=await fixture.getByRole("button",{name:"Play track",exact:true}).count();
    if(!artistTracks)throw new Error("Artist navigation returned no tracks");
    await fixture.getByRole("button",{name:"Add track to queue",exact:true}).first().click();await ready();
    await fixture.getByRole("button",{name:"Back to browse",exact:true}).click();
    if(await fixture.getByRole("button",{name:"Open artist",exact:true}).count()!==artists)throw new Error("Back did not restore artist results");
    await fixture.getByRole("button",{name:"Add artist tracks to queue",exact:true}).nth(1).click();await ready();
    await fixture.getByRole("button",{name:"Playlists",exact:true}).click();
    const playlistSources=await fixture.getByRole("combobox",{name:"Music source"}).evaluate(s=>[...s.options].map(o=>o.value));
    if(JSON.stringify(playlistSources)!==JSON.stringify(["wy"]))throw new Error("Unsupported playlist sources shown");
    await fixture.getByRole("button",{name:"Search",exact:true}).click();await ready();
    const playlists=await fixture.getByRole("button",{name:"Open playlist",exact:true}).count();
    if(!playlists)throw new Error("Playlist search failed");
    await fixture.getByRole("button",{name:"Add playlist to queue",exact:true}).first().click();await ready();
    await fixture.getByRole("button",{name:"Open playlist",exact:true}).first().click();await ready();
    const playlistTracks=await fixture.getByRole("button",{name:"Play track",exact:true}).count();
    if(!playlistTracks)throw new Error("Playlist navigation failed");
    await fixture.getByRole("tab",{name:"Queue",exact:true}).click();
    const queued=await page.evaluate(()=>window.__lxCardCheck.queue.length);
    if(queued!==results+2+artistTracks+playlistTracks)throw new Error("Queue contents are out of order or incomplete");
    if(await fixture.locator("#queue .row").count()<queued)throw new Error("Queued tracks missing from Queue tab");
    const editorResult=await page.evaluate(()=>{
      const editor=customElements.get("lx-music-card").getConfigElement();
      editor.setConfig({type:"custom:lx-music-card",entity:"media_player.lx_server"});
      editor.hass=window.__lxCardCheck.original;document.body.append(editor);
      let config;
      editor.addEventListener("config-changed",e=>config=e.detail.config);
      const name=editor.shadowRoot.querySelector("input");name.value="My Music";name.dispatchEvent(new Event("change"));
      const result={entity:config.entity,title:config.name,players:editor.shadowRoot.querySelectorAll("option").length};
      editor.remove();return result;
    });
    if(editorResult.title!=="My Music"||!editorResult.players)throw new Error("Visual editor failed");
    return {mockedControls:calls.length,songResults:results,artistResults:artists,artistTracks,playlistResults:playlists,playlistTracks,mockedQueuedTracks:queued,editor:editorResult,receiverCommandsSent:0};
  } finally {
    await page.evaluate(()=>{window.__lxCardCheck.preview.remove();delete window.__lxCardCheck;});
  }
})
