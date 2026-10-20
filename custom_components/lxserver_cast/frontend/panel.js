/* Home Assistant supplies authentication, icons, and the application theme. */
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const artwork = value => {
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : ""; }
  catch { return ""; }
};
class LxMusicPanel extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:"open"}); this.tab="player"; this.data=null;
    this.items=[]; this.kind="tracks"; this.trail=[]; this.busy=false; this.error=""; this.source="kw"; this.query="";
    this.shadowRoot.addEventListener("click", event => this.click(event));
    this.shadowRoot.addEventListener("submit", event => { event.preventDefault(); this.search(); });
    this.shadowRoot.addEventListener("change", event => this.change(event));
    this.shadowRoot.addEventListener("keydown", event => {
      const tabs=[...this.shadowRoot.querySelectorAll('[role=tab]')];
      if(!tabs.includes(event.target) || !["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
      event.preventDefault(); const i=tabs.indexOf(event.target);
      const next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(i+(event.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;
      this.tab=tabs[next].dataset.tab; this.render();this.shadowRoot.querySelectorAll('[role=tab]')[next].focus();
    });
  }
  set hass(value) { this._hass=value; if (!this.data) this.refresh(); else this.updatePlayer(); }
  get hass() { return this._hass; }
  connectedCallback() { this.render(); this.timer=setInterval(()=>this.refresh(), 5000); }
  disconnectedCallback() { clearInterval(this.timer); }
  async request(action, extra={}) {
    return this.hass.callWS({type:"lxserver_cast/panel",action,...(this.data?{entry_id:this.data.entry_id}:{}),...extra});
  }
  async refresh() {
    if (!this.hass || this.refreshing || !this.isConnected) return;
    this.refreshing=true;
    try { const first=!this.data; this.data=await this.request("status"); if(first) this.render(); else this.updatePlayer(); }
    catch(error) { this.error=error.message || "Could not connect"; if(!this.data) this.render(); }
    finally { this.refreshing=false; }
  }
  async run(action) {
    this.busy=true; this.error=""; this.render();
    try { await action(); }
    catch(error) { this.error=error.message || "Request failed"; }
    finally { this.busy=false; await this.refresh(); this.render(); }
  }
  async search() {
    this.query=this.shadowRoot.querySelector("input[name=query]")?.value?.trim() || "";
    if(!this.query) return;
    await this.run(async()=>{ this.items=await this.request("search",{query:this.query,source:this.source}); this.kind="tracks"; this.trail=[]; });
  }
  icon(name) { return `<ha-icon icon="mdi:${name}" aria-hidden="true"></ha-icon>`; }
  button(action, icon, label, more="") {
    return `<button type="button" data-action="${action}" title="${label}" aria-label="${label}" ${more} ${this.busy?"disabled":""}>${this.icon(icon)}</button>`;
  }
  async click(event) {
    const button=event.target.closest("button,a[data-nav]"); if(!button) return;
    const action=button.dataset.action;
    if(button.dataset.nav) { event.preventDefault(); history.pushState(null,"",button.getAttribute("href")); window.dispatchEvent(new Event("location-changed")); return; }
    if(button.dataset.tab) { this.tab=button.dataset.tab; this.error=""; this.render(); return; }
    if(action==="menu") { this.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:true,composed:true})); return; }
    if(action==="popular") return this.run(async()=>{this.items=await this.request("popular",{source:"wy"});this.kind="playlists";this.trail=["Popular playlists"];});
    if(action==="favorites") { this.items=this.data?.favorites||[];this.kind="playlists";this.trail=["Favorites"];this.render();return; }
    if(action==="back") { this.items=[];this.trail=[];this.render();return; }
    if(action==="open") { const item=this.items[Number(button.dataset.index)];return this.run(async()=>{this.items=await this.request("playlist",{source:item.source||"wy",list_id:String(item.id)});this.kind="tracks";this.trail=[item.name];}); }
    if(action==="track") { const item=this.items[Number(button.dataset.index)];return this.run(async()=>{await this.request("play",{track_id:item.track_id});this.tab="player";}); }
    if(["play","pause","next","stop"].includes(action)) {
      const service={play:"media_play",pause:"media_pause",next:"media_next_track",stop:"media_stop"}[action];
      return this.run(()=>this.hass.callService("media_player",service,{entity_id:this.playerEntity()}));
    }
  }
  playerEntity() {
    return Object.values(this.hass?.states||{}).find(s=>s.entity_id.startsWith("media_player.") && s.attributes?.lxserver_entry_id===this.data?.entry_id)?.entity_id || "media_player.lx_server";
  }
  async change(event) {
    if(event.target.name==="source") { this.source=event.target.value; return; }
    if(event.target.name==="server") { this.data=await this.request("status",{entry_id:event.target.value});this.items=[];this.trail=[];this.render();return; }
    if(event.target.name==="volume") return this.run(()=>this.hass.callService("media_player","volume_set",{entity_id:this.playerEntity(),volume_level:Number(event.target.value)}));
  }
  updatePlayer() {
    const state=this.hass?.states?.[this.playerEntity()];
    const stamp=JSON.stringify([this.tab,state?.last_updated,this.data?.current,this.data?.upcoming,this.busy]);
    if(stamp===this.lastStamp || this.shadowRoot.activeElement?.name==="volume") return;
    this.lastStamp=stamp;
    if(this.tab==="player") {
      const region=this.shadowRoot.querySelector("#player"); if(region) region.innerHTML=this.playerMarkup();
    }
    if(this.tab==="queue") { const region=this.shadowRoot.querySelector("#queue");if(region)region.innerHTML=this.queueMarkup(); }
  }
  image(url, cls="cover") {
    const safe=artwork(url);
    return safe?`<img class="${cls}" src="${escapeHTML(safe)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:`<div class="${cls} placeholder">${this.icon("music-note")}</div>`;
  }
  playerMarkup() {
    const state=this.hass?.states?.[this.playerEntity()]; const current=this.data?.current;
    const playing=state?.state==="playing"; const volume=state?.attributes?.volume_level ?? this.data?.volume ?? 0.3;
    const target=this.hass?.states?.[this.data?.target];
    return `<section class="now-playing">${current?this.image(current.img):`<img class="cover brand" src="/lxserver_cast_frontend/icon.png" alt="LX Music">`}
      <div class="track-details"><span class="eyebrow">${escapeHTML(target?.attributes?.friendly_name || "LX Music")}</span>
      <h2>${escapeHTML(current?.name || "Ready to play")}</h2><p>${escapeHTML(current?.singer || "Choose music in Browse")}</p>
      <span class="state">${escapeHTML(state?.state || "idle")} · ${escapeHTML(this.data?.quality || "")}</span>
      <div class="transport">${this.button(playing?"pause":"play",playing?"pause":"play",playing?"Pause":"Play",'class="primary"')}${this.button("next","skip-next","Next track")}${this.button("stop","stop","Stop")}</div>
      <label class="volume">${this.icon("volume-high")}<input aria-label="Volume" name="volume" type="range" min="0" max="1" step="0.01" value="${volume}"><output>${Math.round(volume*100)}%</output></label>
      </div></section>`;
  }
  queueMarkup() {
    const songs=this.data?.upcoming||[]; const current=this.data?.current;
    return `${current?`<h3>Playing</h3><div class="row">${this.image(current.img,"thumb")}<div class="copy"><strong>${escapeHTML(current.name)}</strong><small>${escapeHTML(current.singer)}</small></div></div>`:""}
      <h3>Up next <span class="count">${songs.length}</span></h3>${songs.length?songs.map(s=>`<div class="row">${this.image(s.img,"thumb")}<div class="copy"><strong>${escapeHTML(s.name)}</strong><small>${escapeHTML(s.singer)}</small></div><small>${escapeHTML(s.interval)}</small></div>`).join(""):'<p class="empty">The queue is empty.</p>'}`;
  }
  browseMarkup() {
    const rows=this.items.map((item,index)=>`<div class="row">${this.image(item.img,"thumb")}<div class="copy"><strong>${escapeHTML(item.name)}</strong><small>${escapeHTML(item.singer || item.author || (item.total?`${item.total} tracks`:"Playlist"))}</small></div>${this.button(this.kind==="playlists"?"open":"track",this.kind==="playlists"?"chevron-right":"play",this.kind==="playlists"?"Open playlist":"Play track",`data-index="${index}"`)}</div>`).join("");
    return `<form class="search"><input name="query" aria-label="Search music" placeholder="Search songs or artists" value="${escapeHTML(this.query)}" maxlength="200"><select name="source" aria-label="Music source">${[["kw","Kuwo"],["wy","NetEase"],["tx","QQ"],["kg","Kugou"],["mg","Migu"]].map(([v,n])=>`<option value="${v}" ${v===this.source?"selected":""}>${n}</option>`).join("")}</select><button title="Search" aria-label="Search" ${this.busy?"disabled":""}>${this.icon("magnify")}</button></form>
    <div class="browse-links"><button data-action="favorites">${this.icon("heart-outline")} Favorites</button><button data-action="popular">${this.icon("compass-outline")} Popular playlists</button></div>
    ${this.trail.length?`<div class="breadcrumb">${this.button("back","arrow-left","Back to browse")}<h3>${escapeHTML(this.trail.at(-1))}</h3></div>`:""}
    <div class="results" aria-live="polite">${rows||`<p class="empty">${this.busy?"Loading music…":this.trail.length?"No playlists yet.":this.query?"No results.":"Your music starts here."}</p>`}</div>`;
  }
  render() {
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;height:100%;overflow:auto;background:var(--primary-background-color,#f5f6f8);color:var(--primary-text-color,#20242b);font-family:var(--paper-font-body1_-_font-family,Roboto,Arial,sans-serif);letter-spacing:0;color-scheme:light dark}*{box-sizing:border-box}button,input,select{font:inherit;color:inherit}button,a,input,select{touch-action:manipulation}button{cursor:pointer;border:0;background:transparent;min-width:44px;min-height:44px;border-radius:6px;display:inline-flex;align-items:center;justify-content:center;gap:8px}button:hover{background:var(--secondary-background-color,#e8ebef)}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--primary-color,#4a90e2);outline-offset:2px}button:disabled{opacity:.45;cursor:wait}ha-icon{--mdc-icon-size:24px;flex-shrink:0}header{height:64px;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid var(--divider-color,#ddd);background:var(--card-background-color,#fff)}header h1{font-size:20px;margin:0;font-weight:500}header img{width:32px;height:32px}main{max-width:1024px;margin:auto;padding:24px}nav{display:flex;gap:8px;border-bottom:1px solid var(--divider-color,#ddd);margin-bottom:24px;overflow:auto}nav button{border-radius:0;flex:1;min-width:74px;padding:12px 8px;border-bottom:3px solid transparent}nav button[aria-selected=true]{border-bottom-color:var(--primary-color,#4a90e2);color:var(--primary-color,#4a90e2)}h2{font-size:26px;line-height:1.25;margin:8px 0;overflow-wrap:anywhere}h3{font-size:16px;font-weight:500}.now-playing{display:grid;grid-template-columns:minmax(180px,320px) minmax(0,1fr);align-items:center;gap:32px;padding:12px 0 32px}.cover{width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px}.brand{object-fit:contain;padding:32px;background:var(--card-background-color,#fff)}.placeholder{display:grid;place-items:center;background:var(--secondary-background-color,#e8ebef);color:var(--secondary-text-color,#667)}.placeholder ha-icon{--mdc-icon-size:40px}.eyebrow,.state,small{font-size:13px;color:var(--secondary-text-color,#667)}p{color:var(--secondary-text-color,#667);line-height:1.5}.transport{display:flex;align-items:center;gap:16px;margin:24px 0}.transport button.primary{width:64px;height:64px;border-radius:50%;background:var(--primary-color,#4a90e2);color:var(--text-primary-color,#fff)}.volume{display:flex;align-items:center;gap:12px}.volume input{min-width:0;flex:1;accent-color:var(--primary-color,#4a90e2)}.volume output{min-width:44px;text-align:right;font-size:13px}.search{display:flex;gap:8px;margin-bottom:16px}.search input{flex:1;min-width:0}.search input,select{height:44px;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#ddd);border-radius:6px;padding:0 12px}.browse-links{display:flex;gap:12px;flex-wrap:wrap}.browse-links button{padding:0 12px}.breadcrumb{display:flex;align-items:center;gap:8px;margin-top:20px}.row{display:flex;gap:12px;align-items:center;min-height:70px;padding:10px 0;border-bottom:1px solid var(--divider-color,#ddd)}.thumb{width:48px;height:48px;aspect-ratio:1;object-fit:cover;border-radius:4px;flex-shrink:0}.copy{flex:1;min-width:0}.copy strong,.copy small{display:block;overflow-wrap:anywhere}.copy strong{font-size:14px;font-weight:500;line-height:1.4}.copy small{margin-top:4px}.empty{padding:48px 0;text-align:center}.count{font-size:13px;color:var(--secondary-text-color,#667);margin-left:8px}.error{padding:12px;border-left:3px solid var(--error-color,#c33);background:var(--card-background-color,#fff);margin-bottom:16px;overflow-wrap:anywhere}a{color:var(--primary-color,#4a90e2);text-decoration:none;display:inline-flex;align-items:center;gap:8px;min-height:44px}.settings-line{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:56px;border-bottom:1px solid var(--divider-color,#ddd)}.settings-line span:last-child{color:var(--secondary-text-color,#667);text-align:right;overflow-wrap:anywhere}section select[name=server]{max-width:100%}@media(max-width:600px){main{padding:16px}.now-playing{grid-template-columns:1fr;gap:20px}.cover{max-width:260px;justify-self:center}.track-details{width:100%}h2{font-size:22px}nav button{flex-direction:column;gap:4px;font-size:12px}header{height:56px}.search{flex-wrap:wrap}.search input{flex-basis:calc(100% - 56px);order:0}.search button{order:1}.search select{order:2;width:100%}.settings-line{align-items:flex-start;padding:12px 0}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
    </style><header>${this.button("menu","menu","Open sidebar")}<img src="/lxserver_cast_frontend/icon.png" alt=""><h1>LX Music</h1></header><main>
    <nav role="tablist" aria-label="LX Music">${[["player","play-circle-outline","Player"],["browse","magnify","Browse"],["queue","playlist-music","Queue"],["settings","cog-outline","Settings"]].map(([key,icon,label])=>`<button role="tab" data-tab="${key}" aria-selected="${this.tab===key}">${this.icon(icon)}${label}</button>`).join("")}</nav>
    ${this.error?`<div role="alert" class="error">${escapeHTML(this.error)}</div>`:""}
    ${!this.data?'<p class="empty">Connecting to LX Server…</p>':this.tab==="player"?`<div id="player">${this.playerMarkup()}</div>`:this.tab==="browse"?this.browseMarkup():this.tab==="queue"?`<div id="queue">${this.queueMarkup()}</div>`:`<section><h3>Library</h3><select name="server" aria-label="LX Server account">${this.data.entries.map(e=>`<option value="${escapeHTML(e.entry_id)}" ${e.entry_id===this.data.entry_id?"selected":""}>${escapeHTML(e.title)}</option>`).join("")}</select><div class="settings-line"><span>Output</span><span>${escapeHTML(this.hass?.states?.[this.data.target]?.attributes?.friendly_name||"No output selected")}</span></div><div class="settings-line"><span>Audio quality</span><span>${escapeHTML(this.data.quality)}</span></div><div class="settings-line"><span>Default volume</span><span>${Math.round(this.data.volume*100)}%</span></div><p><a data-nav="true" href="/config/integrations/integration/lxserver_cast">${this.icon("tune")} Integration settings</a></p></section>`}
    </main>`;
  }
}
if(!customElements.get("lx-music-panel"))customElements.define("lx-music-panel",LxMusicPanel);
