import {LxMusicPanel, escapeHTML} from "./panel.js?v=0.4.0";

class LxMusicCard extends LxMusicPanel {
  constructor() { super(); this.cardMode=true; }
  connectedCallback() { this.setAttribute("data-card","");super.connectedCallback(); }
  setConfig(config) {
    if(config.entity && !config.entity.startsWith("media_player.")) throw new Error("Choose an LX Server media player");
    this._config={...config}; this.data=null; this.items=[]; this.trail=[]; this.backStack=[];
    this.render(); this.refresh();
  }
  getCardSize() { return this.tab==="player"?6:9; }
  getGridOptions() { return {columns:12,rows:6,min_columns:6,min_rows:5}; }
  static getStubConfig(hass) {
    const entity=Object.values(hass.states).find(s=>s.entity_id.startsWith("media_player.") && s.attributes.lxserver_entry_id)?.entity_id;
    return {entity:entity||"media_player.lx_server"};
  }
  static getConfigElement() { return document.createElement("lx-music-card-editor"); }
}

class LxMusicCardEditor extends HTMLElement {
  constructor() { super();this.attachShadow({mode:"open"}); }
  setConfig(config) { this.config={...config};this.render(); }
  set hass(value) { this._hass=value;this.render(); }
  render() {
    if(!this._hass||!this.config)return;
    if(!this.shadowRoot.firstChild) {
      this.shadowRoot.innerHTML=`<style>:host{display:grid;gap:16px;padding:12px 0}label{display:grid;gap:6px}input,select{font:inherit;min-height:44px;padding:12px;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:6px}</style><label>LX Server player<select aria-label="LX Server player"></select></label><label>Card title<input name="name" aria-label="Card title"></label>`;
      this.shadowRoot.querySelector("select").addEventListener("change",e=>this.update("entity",e.target.value));
      this.shadowRoot.querySelector("input").addEventListener("change",e=>this.update("name",e.target.value));
    }
    const picker=this.shadowRoot.querySelector("select");
    const entities=Object.values(this._hass.states).filter(s=>s.entity_id.startsWith("media_player.")&&s.attributes.lxserver_entry_id);
    picker.innerHTML=entities.map(s=>`<option value="${escapeHTML(s.entity_id)}">${escapeHTML(s.attributes.friendly_name||s.entity_id)}</option>`).join("");
    picker.value=this.config.entity||"";
    const input=this.shadowRoot.querySelector("input");
    if(this.shadowRoot.activeElement!==input)input.value=this.config.name||"";
  }
  update(key,value) {
    if(this.config[key]===value)return;
    this.config={...this.config,[key]:value};
    this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this.config},bubbles:true,composed:true}));
  }
}
if(!customElements.get("lx-music-card"))customElements.define("lx-music-card",LxMusicCard);
if(!customElements.get("lx-music-card-editor"))customElements.define("lx-music-card-editor",LxMusicCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(card=>card.type==="lx-music-card"))window.customCards.push({type:"lx-music-card",name:"LX Music",preview:true,description:"LX Music player, volume, Cast outputs and library"});
