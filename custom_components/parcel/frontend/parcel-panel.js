var d5=Object.defineProperty;var m5=(L,C,H)=>C in L?d5(L,C,{enumerable:!0,configurable:!0,writable:!0,value:H}):L[C]=H;var M1=(L,C,H)=>m5(L,typeof C!="symbol"?C+"":C,H);var q=globalThis,j=q.ShadowRoot&&(q.ShadyCSS===void 0||q.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,r1=Symbol(),O1=new WeakMap,E=class{constructor(C,H,V){if(this._$cssResult$=!0,V!==r1)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=C,this.t=H}get styleSheet(){let C=this.o,H=this.t;if(j&&C===void 0){let V=H!==void 0&&H.length===1;V&&(C=O1.get(H)),C===void 0&&((this.o=C=new CSSStyleSheet).replaceSync(this.cssText),V&&O1.set(H,C))}return C}toString(){return this.cssText}},g1=L=>new E(typeof L=="string"?L:L+"",void 0,r1),e1=(L,...C)=>{let H=L.length===1?L[0]:C.reduce((V,M,r)=>V+(e=>{if(e._$cssResult$===!0)return e.cssText;if(typeof e=="number")return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(M)+L[r+1],L[0]);return new E(H,L,r1)},f1=(L,C)=>{if(j)L.adoptedStyleSheets=C.map(H=>H instanceof CSSStyleSheet?H:H.styleSheet);else for(let H of C){let V=document.createElement("style"),M=q.litNonce;M!==void 0&&V.setAttribute("nonce",M),V.textContent=H.cssText,L.appendChild(V)}},t1=j?L=>L:L=>L instanceof CSSStyleSheet?(C=>{let H="";for(let V of C.cssRules)H+=V.cssText;return g1(H)})(L):L;var{is:n5,defineProperty:l5,getOwnPropertyDescriptor:x5,getOwnPropertyNames:v5,getOwnPropertySymbols:Z5,getPrototypeOf:s5}=Object,X=globalThis,k1=X.trustedTypes,u5=k1?k1.emptyScript:"",S5=X.reactiveElementPolyfillSupport,_=(L,C)=>L,i1={toAttribute(L,C){switch(C){case Boolean:L=L?u5:null;break;case Object:case Array:L=L==null?L:JSON.stringify(L)}return L},fromAttribute(L,C){let H=L;switch(C){case Boolean:H=L!==null;break;case Number:H=L===null?null:Number(L);break;case Object:case Array:try{H=JSON.parse(L)}catch{H=null}}return H}},y1=(L,C)=>!n5(L,C),b1={attribute:!0,type:String,converter:i1,reflect:!1,useDefault:!1,hasChanged:y1};Symbol.metadata??=Symbol("metadata"),X.litPropertyMetadata??=new WeakMap;var h=class extends HTMLElement{static addInitializer(C){this._$Ei(),(this.l??=[]).push(C)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(C,H=b1){if(H.state&&(H.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(C)&&((H=Object.create(H)).wrapped=!0),this.elementProperties.set(C,H),!H.noAccessor){let V=Symbol(),M=this.getPropertyDescriptor(C,V,H);M!==void 0&&l5(this.prototype,C,M)}}static getPropertyDescriptor(C,H,V){let{get:M,set:r}=x5(this.prototype,C)??{get(){return this[H]},set(e){this[H]=e}};return{get:M,set(e){let i=M?.call(this);r?.call(this,e),this.requestUpdate(C,i,V)},configurable:!0,enumerable:!0}}static getPropertyOptions(C){return this.elementProperties.get(C)??b1}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;let C=s5(this);C.finalize(),C.l!==void 0&&(this.l=[...C.l]),this.elementProperties=new Map(C.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){let H=this.properties,V=[...v5(H),...Z5(H)];for(let M of V)this.createProperty(M,H[M])}let C=this[Symbol.metadata];if(C!==null){let H=litPropertyMetadata.get(C);if(H!==void 0)for(let[V,M]of H)this.elementProperties.set(V,M)}this._$Eh=new Map;for(let[H,V]of this.elementProperties){let M=this._$Eu(H,V);M!==void 0&&this._$Eh.set(M,H)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(C){let H=[];if(Array.isArray(C)){let V=new Set(C.flat(1/0).reverse());for(let M of V)H.unshift(t1(M))}else C!==void 0&&H.push(t1(C));return H}static _$Eu(C,H){let V=H.attribute;return V===!1?void 0:typeof V=="string"?V:typeof C=="string"?C.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(C=>this.enableUpdating=C),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(C=>C(this))}addController(C){(this._$EO??=new Set).add(C),this.renderRoot!==void 0&&this.isConnected&&C.hostConnected?.()}removeController(C){this._$EO?.delete(C)}_$E_(){let C=new Map,H=this.constructor.elementProperties;for(let V of H.keys())this.hasOwnProperty(V)&&(C.set(V,this[V]),delete this[V]);C.size>0&&(this._$Ep=C)}createRenderRoot(){let C=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return f1(C,this.constructor.elementStyles),C}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(C=>C.hostConnected?.())}enableUpdating(C){}disconnectedCallback(){this._$EO?.forEach(C=>C.hostDisconnected?.())}attributeChangedCallback(C,H,V){this._$AK(C,V)}_$ET(C,H){let V=this.constructor.elementProperties.get(C),M=this.constructor._$Eu(C,V);if(M!==void 0&&V.reflect===!0){let r=(V.converter?.toAttribute!==void 0?V.converter:i1).toAttribute(H,V.type);this._$Em=C,r==null?this.removeAttribute(M):this.setAttribute(M,r),this._$Em=null}}_$AK(C,H){let V=this.constructor,M=V._$Eh.get(C);if(M!==void 0&&this._$Em!==M){let r=V.getPropertyOptions(M),e=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:i1;this._$Em=M;let i=e.fromAttribute(H,r.type);this[M]=i??this._$Ej?.get(M)??i,this._$Em=null}}requestUpdate(C,H,V,M=!1,r){if(C!==void 0){let e=this.constructor;if(M===!1&&(r=this[C]),V??=e.getPropertyOptions(C),!((V.hasChanged??y1)(r,H)||V.useDefault&&V.reflect&&r===this._$Ej?.get(C)&&!this.hasAttribute(e._$Eu(C,V))))return;this.C(C,H,V)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(C,H,{useDefault:V,reflect:M,wrapped:r},e){V&&!(this._$Ej??=new Map).has(C)&&(this._$Ej.set(C,e??H??this[C]),r!==!0||e!==void 0)||(this._$AL.has(C)||(this.hasUpdated||V||(H=void 0),this._$AL.set(C,H)),M===!0&&this._$Em!==C&&(this._$Eq??=new Set).add(C))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(H){Promise.reject(H)}let C=this.scheduleUpdate();return C!=null&&await C,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[M,r]of this._$Ep)this[M]=r;this._$Ep=void 0}let V=this.constructor.elementProperties;if(V.size>0)for(let[M,r]of V){let{wrapped:e}=r,i=this[M];e!==!0||this._$AL.has(M)||i===void 0||this.C(M,void 0,r,i)}}let C=!1,H=this._$AL;try{C=this.shouldUpdate(H),C?(this.willUpdate(H),this._$EO?.forEach(V=>V.hostUpdate?.()),this.update(H)):this._$EM()}catch(V){throw C=!1,this._$EM(),V}C&&this._$AE(H)}willUpdate(C){}_$AE(C){this._$EO?.forEach(H=>H.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(C)),this.updated(C)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(C){return!0}update(C){this._$Eq&&=this._$Eq.forEach(H=>this._$ET(H,this[H])),this._$EM()}updated(C){}firstUpdated(C){}};h.elementStyles=[],h.shadowRootOptions={mode:"open"},h[_("elementProperties")]=new Map,h[_("finalized")]=new Map,S5?.({ReactiveElement:h}),(X.reactiveElementVersions??=[]).push("2.1.2");var n1=globalThis,w1=L=>L,Y=n1.trustedTypes,B1=Y?Y.createPolicy("lit-html",{createHTML:L=>L}):void 0,E1="$lit$",f=`lit$${Math.random().toFixed(9).slice(2)}$`,_1="?"+f,c5=`<${_1}>`,B=document,N=()=>B.createComment(""),W=L=>L===null||typeof L!="object"&&typeof L!="function",l1=Array.isArray,h5=L=>l1(L)||typeof L?.[Symbol.iterator]=="function",o1=`[ 	
\f\r]`,$=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,P1=/-->/g,T1=/>/g,y=RegExp(`>|${o1}(?:([^\\s"'>=/]+)(${o1}*=${o1}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),F1=/'/g,R1=/"/g,$1=/^(?:script|style|textarea|title)$/i,x1=L=>(C,...H)=>({_$litType$:L,strings:C,values:H}),A=x1(1),N1=x1(2),U5=x1(3),P=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),D1=new WeakMap,w=B.createTreeWalker(B,129);function W1(L,C){if(!l1(L)||!L.hasOwnProperty("raw"))throw Error("invalid template strings array");return B1!==void 0?B1.createHTML(C):C}var O5=(L,C)=>{let H=L.length-1,V=[],M,r=C===2?"<svg>":C===3?"<math>":"",e=$;for(let i=0;i<H;i++){let t=L[i],p,n,d=-1,a=0;for(;a<t.length&&(e.lastIndex=a,n=e.exec(t),n!==null);)a=e.lastIndex,e===$?n[1]==="!--"?e=P1:n[1]!==void 0?e=T1:n[2]!==void 0?($1.test(n[2])&&(M=RegExp("</"+n[2],"g")),e=y):n[3]!==void 0&&(e=y):e===y?n[0]===">"?(e=M??$,d=-1):n[1]===void 0?d=-2:(d=e.lastIndex-n[2].length,p=n[1],e=n[3]===void 0?y:n[3]==='"'?R1:F1):e===R1||e===F1?e=y:e===P1||e===T1?e=$:(e=y,M=void 0);let m=e===y&&L[i+1].startsWith("/>")?" ":"";r+=e===$?t+c5:d>=0?(V.push(p),t.slice(0,d)+E1+t.slice(d)+f+m):t+f+(d===-2?i:m)}return[W1(L,r+(L[H]||"<?>")+(C===2?"</svg>":C===3?"</math>":"")),V]},I=class L{constructor({strings:C,_$litType$:H},V){let M;this.parts=[];let r=0,e=0,i=C.length-1,t=this.parts,[p,n]=O5(C,H);if(this.el=L.createElement(p,V),w.currentNode=this.el.content,H===2||H===3){let d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(M=w.nextNode())!==null&&t.length<i;){if(M.nodeType===1){if(M.hasAttributes())for(let d of M.getAttributeNames())if(d.endsWith(E1)){let a=n[e++],m=M.getAttribute(d).split(f),x=/([.?@])?(.*)/.exec(a);t.push({type:1,index:r,name:x[2],strings:m,ctor:x[1]==="."?A1:x[1]==="?"?p1:x[1]==="@"?d1:D}),M.removeAttribute(d)}else d.startsWith(f)&&(t.push({type:6,index:r}),M.removeAttribute(d));if($1.test(M.tagName)){let d=M.textContent.split(f),a=d.length-1;if(a>0){M.textContent=Y?Y.emptyScript:"";for(let m=0;m<a;m++)M.append(d[m],N()),w.nextNode(),t.push({type:2,index:++r});M.append(d[a],N())}}}else if(M.nodeType===8)if(M.data===_1)t.push({type:2,index:r});else{let d=-1;for(;(d=M.data.indexOf(f,d+1))!==-1;)t.push({type:7,index:r}),d+=f.length-1}r++}}static createElement(C,H){let V=B.createElement("template");return V.innerHTML=C,V}};function R(L,C,H=L,V){if(C===P)return C;let M=V!==void 0?H._$Co?.[V]:H._$Cl,r=W(C)?void 0:C._$litDirective$;return M?.constructor!==r&&(M?._$AO?.(!1),r===void 0?M=void 0:(M=new r(L),M._$AT(L,H,V)),V!==void 0?(H._$Co??=[])[V]=M:H._$Cl=M),M!==void 0&&(C=R(L,M._$AS(L,C.values),M,V)),C}var a1=class{constructor(C,H){this._$AV=[],this._$AN=void 0,this._$AD=C,this._$AM=H}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(C){let{el:{content:H},parts:V}=this._$AD,M=(C?.creationScope??B).importNode(H,!0);w.currentNode=M;let r=w.nextNode(),e=0,i=0,t=V[0];for(;t!==void 0;){if(e===t.index){let p;t.type===2?p=new U(r,r.nextSibling,this,C):t.type===1?p=new t.ctor(r,t.name,t.strings,this,C):t.type===6&&(p=new m1(r,this,C)),this._$AV.push(p),t=V[++i]}e!==t?.index&&(r=w.nextNode(),e++)}return w.currentNode=B,M}p(C){let H=0;for(let V of this._$AV)V!==void 0&&(V.strings!==void 0?(V._$AI(C,V,H),H+=V.strings.length-2):V._$AI(C[H])),H++}},U=class L{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(C,H,V,M){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=C,this._$AB=H,this._$AM=V,this.options=M,this._$Cv=M?.isConnected??!0}get parentNode(){let C=this._$AA.parentNode,H=this._$AM;return H!==void 0&&C?.nodeType===11&&(C=H.parentNode),C}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(C,H=this){C=R(this,C,H),W(C)?C===l||C==null||C===""?(this._$AH!==l&&this._$AR(),this._$AH=l):C!==this._$AH&&C!==P&&this._(C):C._$litType$!==void 0?this.$(C):C.nodeType!==void 0?this.T(C):h5(C)?this.k(C):this._(C)}O(C){return this._$AA.parentNode.insertBefore(C,this._$AB)}T(C){this._$AH!==C&&(this._$AR(),this._$AH=this.O(C))}_(C){this._$AH!==l&&W(this._$AH)?this._$AA.nextSibling.data=C:this.T(B.createTextNode(C)),this._$AH=C}$(C){let{values:H,_$litType$:V}=C,M=typeof V=="number"?this._$AC(C):(V.el===void 0&&(V.el=I.createElement(W1(V.h,V.h[0]),this.options)),V);if(this._$AH?._$AD===M)this._$AH.p(H);else{let r=new a1(M,this),e=r.u(this.options);r.p(H),this.T(e),this._$AH=r}}_$AC(C){let H=D1.get(C.strings);return H===void 0&&D1.set(C.strings,H=new I(C)),H}k(C){l1(this._$AH)||(this._$AH=[],this._$AR());let H=this._$AH,V,M=0;for(let r of C)M===H.length?H.push(V=new L(this.O(N()),this.O(N()),this,this.options)):V=H[M],V._$AI(r),M++;M<H.length&&(this._$AR(V&&V._$AB.nextSibling,M),H.length=M)}_$AR(C=this._$AA.nextSibling,H){for(this._$AP?.(!1,!0,H);C!==this._$AB;){let V=w1(C).nextSibling;w1(C).remove(),C=V}}setConnected(C){this._$AM===void 0&&(this._$Cv=C,this._$AP?.(C))}},D=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(C,H,V,M,r){this.type=1,this._$AH=l,this._$AN=void 0,this.element=C,this.name=H,this._$AM=M,this.options=r,V.length>2||V[0]!==""||V[1]!==""?(this._$AH=Array(V.length-1).fill(new String),this.strings=V):this._$AH=l}_$AI(C,H=this,V,M){let r=this.strings,e=!1;if(r===void 0)C=R(this,C,H,0),e=!W(C)||C!==this._$AH&&C!==P,e&&(this._$AH=C);else{let i=C,t,p;for(C=r[0],t=0;t<r.length-1;t++)p=R(this,i[V+t],H,t),p===P&&(p=this._$AH[t]),e||=!W(p)||p!==this._$AH[t],p===l?C=l:C!==l&&(C+=(p??"")+r[t+1]),this._$AH[t]=p}e&&!M&&this.j(C)}j(C){C===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,C??"")}},A1=class extends D{constructor(){super(...arguments),this.type=3}j(C){this.element[this.name]=C===l?void 0:C}},p1=class extends D{constructor(){super(...arguments),this.type=4}j(C){this.element.toggleAttribute(this.name,!!C&&C!==l)}},d1=class extends D{constructor(C,H,V,M,r){super(C,H,V,M,r),this.type=5}_$AI(C,H=this){if((C=R(this,C,H,0)??l)===P)return;let V=this._$AH,M=C===l&&V!==l||C.capture!==V.capture||C.once!==V.once||C.passive!==V.passive,r=C!==l&&(V===l||M);M&&this.element.removeEventListener(this.name,this,V),r&&this.element.addEventListener(this.name,this,C),this._$AH=C}handleEvent(C){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,C):this._$AH.handleEvent(C)}},m1=class{constructor(C,H,V){this.element=C,this.type=6,this._$AN=void 0,this._$AM=H,this.options=V}get _$AU(){return this._$AM._$AU}_$AI(C){R(this,C)}};var g5=n1.litHtmlPolyfillSupport;g5?.(I,U),(n1.litHtmlVersions??=[]).push("3.3.3");var I1=(L,C,H)=>{let V=H?.renderBefore??C,M=V._$litPart$;if(M===void 0){let r=H?.renderBefore??null;V._$litPart$=M=new U(C.insertBefore(N(),r),r,void 0,H??{})}return M._$AI(L),M};var v1=globalThis,k=class extends h{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let C=super.createRenderRoot();return this.renderOptions.renderBefore??=C.firstChild,C}update(C){let H=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(C),this._$Do=I1(H,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return P}};k._$litElement$=!0,k.finalized=!0,v1.litElementHydrateSupport?.({LitElement:k});var f5=v1.litElementPolyfillSupport;f5?.({LitElement:k});(v1.litElementVersions??=[]).push("4.2.2");async function U1(L){try{if(navigator.clipboard?.writeText)return await navigator.clipboard.writeText(L),!0}catch{}let C=document.createElement("textarea");C.value=L,C.setAttribute("readonly",""),C.setAttribute("aria-hidden","true"),C.style.cssText="position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none;",document.body.appendChild(C);try{return C.select(),C.setSelectionRange(0,L.length),document.execCommand("copy")}catch{return!1}finally{C.remove()}}var J=(L,C)=>{let H=new Date(`${L}T12:00:00Z`);return H.setUTCDate(H.getUTCDate()+C),H.toISOString().slice(0,10)},G=(L,C)=>Math.round((Date.parse(`${C}T12:00:00Z`)-Date.parse(`${L}T12:00:00Z`))/864e5),S=L=>{if(!L)return null;let C=new Date(L);return Number.isNaN(C.getTime())?null:C};function Z1(L){let C=L?.locale?.language||L?.language||navigator.language||"en",H=L?.locale?.time_format,V=H==="12"?!0:H==="24"?!1:void 0,M=L?.locale?.time_zone==="server"?L?.config?.time_zone:void 0,r=new Map,e=(a,m,x=M)=>{let s=`${a}|${x||""}`;if(!r.has(s))try{r.set(s,new Intl.DateTimeFormat(C,x?{...m,timeZone:x}:m))}catch{r.set(s,new Intl.DateTimeFormat("en",x?{...m,timeZone:x}:m))}return r.get(s)},i=a=>{let m={};for(let x of e("parts",{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(a))m[x.type]=x.value;return m},t=a=>new Date(`${a}T12:00:00Z`),p=a=>(a.match(/\s?[^\d\s:.]+$/)||[""])[0],n=(a,m,x)=>{let s=d.time(a),c=d.time(m),g=p(s);return g&&g===p(c)?x(s.slice(0,-g.length),c):x(s,c)},d={ymd(a){let m=i(a);return`${m.year}-${m.month}-${m.day}`},hours(a){let m=i(a);return Number(m.hour)%24+Number(m.minute)/60},time(a){let x=i(a).minute==="00",s=e("probe",{hour:"numeric",hour12:V}).formatToParts(a).some(c=>c.type==="dayPeriod");return x&&s?e("hour",{hour:"numeric",hour12:V}).format(a):e("time",{hour:"numeric",minute:"2-digit",hour12:V}).format(a)},window:(a,m)=>n(a,m,(x,s)=>`${x}\u2013${s}`),between:(a,m)=>n(a,m,(x,s)=>`between ${x} and ${s}`),weekday:(a,m="long")=>e(`wd-${m}`,{weekday:m},"UTC").format(t(a)),monthDay:a=>e("md",{month:"short",day:"numeric"},"UTC").format(t(a)),longDate:a=>e("ld",{weekday:"long",month:"long",day:"numeric"},"UTC").format(t(a)),shortDate:a=>e("sd",{weekday:"short",month:"short",day:"numeric"},"UTC").format(t(a)),monthShort:a=>e("mon",{month:"short"},"UTC").format(t(a)),dayNumber:a=>Number(a.slice(8,10)),hourLabel:a=>e("hl",{hour:"numeric",hour12:V},"UTC").format(new Date(Date.UTC(2e3,0,1,a%24)))};return d}var G1="M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z";var Q1="M12,2L1,21H23M12,6L19.53,19H4.47M11,10V14H13V10M11,16V18H13V16";var z1="M16.67,4H15V2H9V4H7.33A1.33,1.33 0 0,0 6,5.33V20.66C6,21.4 6.6,22 7.33,22H16.66C17.4,22 18,21.4 18,20.67V5.33C18,4.6 17.4,4 16.67,4M11,20V14.5H9L13,7V12.5H15";var K1="M19 2L14 6.5V17.5L19 13V2M6.5 5C4.55 5 2.45 5.4 1 6.5V21.16C1 21.41 1.25 21.66 1.5 21.66C1.6 21.66 1.65 21.59 1.75 21.59C3.1 20.94 5.05 20.5 6.5 20.5C8.45 20.5 10.55 20.9 12 22C13.35 21.15 15.8 20.5 17.5 20.5C19.15 20.5 20.85 20.81 22.25 21.56C22.35 21.61 22.4 21.59 22.5 21.59C22.75 21.59 23 21.34 23 21.09V6.5C22.4 6.05 21.75 5.75 21 5.5V19C19.9 18.65 18.7 18.5 17.5 18.5C15.8 18.5 13.35 19.15 12 20V6.5C10.55 5.4 8.45 5 6.5 5Z";var q1="M4,4H7L9,2H15L17,4H20A2,2 0 0,1 22,6V18A2,2 0 0,1 20,20H4A2,2 0 0,1 2,18V6A2,2 0 0,1 4,4M12,7A5,5 0 0,0 7,12A5,5 0 0,0 12,17A5,5 0 0,0 17,12A5,5 0 0,0 12,7M12,9A3,3 0 0,1 15,12A3,3 0 0,1 12,15A3,3 0 0,1 9,12A3,3 0 0,1 12,9Z";var j1="M17,19H7V5H17M17,1H7C5.89,1 5,1.89 5,3V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V3C19,1.89 18.1,1 17,1Z";var X1="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z",Y1="M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z";var J1="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";var C2="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";var H2="M19,3H14.82C14.25,1.44 12.53,0.64 11,1.2C10.14,1.5 9.5,2.16 9.18,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M12,3A1,1 0 0,1 13,4A1,1 0 0,1 12,5A1,1 0 0,1 11,4A1,1 0 0,1 12,3M7,7H17V5H19V19H5V5H7V7M17,11H7V9H17V11M15,15H7V13H15V15Z";var V2="M11 7V13L16.2 16.1L17 14.9L12.5 12.2V7H11M20 12V18H22V12H20M20 20V22H22V20H20M18 20C16.3 21.3 14.3 22 12 22C6.5 22 2 17.5 2 12S6.5 2 12 2C16.8 2 20.9 5.4 21.8 10H19.7C18.8 6.6 15.7 4 12 4C7.6 4 4 7.6 4 12S7.6 20 12 20C14.4 20 16.5 18.9 18 17.3V20Z";var L2="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z";var M2="M2,21H20V19H2M20,8H18V5H20M20,3H4V13A4,4 0 0,0 8,17H14A4,4 0 0,0 18,13V10H20A2,2 0 0,0 22,8V5C22,3.89 21.1,3 20,3Z";var r2="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";var e2="M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";var t2="M10.85,2L9.18,4.5L10.32,5.25L7.14,10C7.1,10 7.05,10 7,10A2,2 0 0,0 5,12C5,12.94 5.66,13.75 6.58,13.95L10.62,20H7V22H17V20H13L8.53,13.28C8.83,12.92 9,12.47 9,12C9,11.7 8.93,11.4 8.8,11.13L12,6.37C11.78,8.05 12.75,9.89 14.45,11L18.89,4.37C17.2,3.24 15.12,3.04 13.65,3.87L10.85,2M18.33,7L16.67,9.5C17.35,9.95 18.29,9.77 18.75,9.08C19.21,8.39 19,7.46 18.33,7Z";var i2="M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z";var o2="M20,10C22,13 17,22 15,22C13,22 13,21 12,21C11,21 11,22 9,22C7,22 2,13 4,10C6,7 9,7 11,8V5C5.38,8.07 4.11,3.78 4.11,3.78C4.11,3.78 6.77,0.19 11,5V3H13V8C15,7 18,7 20,10Z";var a2="M7,6H17A6,6 0 0,1 23,12A6,6 0 0,1 17,18C15.22,18 13.63,17.23 12.53,16H11.47C10.37,17.23 8.78,18 7,18A6,6 0 0,1 1,12A6,6 0 0,1 7,6M6,9V11H4V13H6V15H8V13H10V11H8V9H6M15.5,12A1.5,1.5 0 0,0 14,13.5A1.5,1.5 0 0,0 15.5,15A1.5,1.5 0 0,0 17,13.5A1.5,1.5 0 0,0 15.5,12M18.5,9A1.5,1.5 0 0,0 17,10.5A1.5,1.5 0 0,0 18.5,12A1.5,1.5 0 0,0 20,10.5A1.5,1.5 0 0,0 18.5,9Z";var A2="M9.06,1.93C7.17,1.92 5.33,3.74 6.17,6H3A2,2 0 0,0 1,8V10A1,1 0 0,0 2,11H11V8H13V11H22A1,1 0 0,0 23,10V8A2,2 0 0,0 21,6H17.83C19,2.73 14.6,0.42 12.57,3.24L12,4L11.43,3.22C10.8,2.33 9.93,1.94 9.06,1.93M9,4C9.89,4 10.34,5.08 9.71,5.71C9.08,6.34 8,5.89 8,5A1,1 0 0,1 9,4M15,4C15.89,4 16.34,5.08 15.71,5.71C15.08,6.34 14,5.89 14,5A1,1 0 0,1 15,4M2,12V20A2,2 0 0,0 4,22H20A2,2 0 0,0 22,20V12H13V20H11V12H2Z";var p2="M15.5,21.27L14.66,21.18C13.9,21.11 13.25,20.6 13,19.87C12.47,17.91 12.47,15.83 13,13.87C15.32,13.4 17,11.37 17,9C17,7 15,2 15,2H9C9,2 7,7 7,9C7,11.38 8.67,13.42 11,13.9C11.53,15.86 11.53,17.94 11,19.9C10.76,20.62 10.12,21.13 9.37,21.21L8.5,21.3C8.5,21.3 8,21.28 8,22H16C16,21.28 15.5,21.27 15.5,21.27M9.44,7L10.44,4H13.56L14.56,7H9.44Z";var d2="M13.78 15.3L19.78 21.3L21.89 19.14L15.89 13.14L13.78 15.3M17.5 10.1C17.11 10.1 16.69 10.05 16.36 9.91L4.97 21.25L2.86 19.14L10.27 11.74L8.5 9.96L7.78 10.66L6.33 9.25V12.11L5.63 12.81L2.11 9.25L2.81 8.55H5.62L4.22 7.14L7.78 3.58C8.95 2.41 10.83 2.41 12 3.58L9.89 5.74L11.3 7.14L10.59 7.85L12.38 9.63L14.2 7.75C14.06 7.42 14 7 14 6.63C14 4.66 15.56 3.11 17.5 3.11C18.09 3.11 18.61 3.25 19.08 3.53L16.41 6.2L17.91 7.7L20.58 5.03C20.86 5.5 21 6 21 6.63C21 8.55 19.45 10.1 17.5 10.1Z";var m2="M12,1C7,1 3,5 3,10V17A3,3 0 0,0 6,20H9V12H5V10A7,7 0 0,1 12,3A7,7 0 0,1 19,10V12H15V20H18A3,3 0 0,0 21,17V10C21,5 16.97,1 12,1Z";var n2="M11,18H13V16H11V18M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,6A4,4 0 0,0 8,10H10A2,2 0 0,1 12,8A2,2 0 0,1 14,10C14,12 11,11.75 11,15H13C13,12.75 16,12.5 16,10A4,4 0 0,0 12,6Z";var l2="M12 5.7L17 10.2V18H7V10.2L12 5.7M19 20V12H22L12 3L2 12H5V20M13 8H11V13H13V8M13 15H11V17H13V15";var x2="M9,13H15V19H18V10L12,5.5L6,10V19H9V13M4,21V9L12,3L20,9V21H4Z";var v2="M10,14.29L6.5,19H17.46L14.75,15.46L12.78,17.8L10,14.29M5,21V7H18.96V21H5M12,2.4L14.61,5.03H9.37L12,2.4M5,5.03C4.5,5.03 4,5.22 3.61,5.61C3.2,6 3,6.46 3,7V21C3,21.5 3.2,22 3.61,22.39C4,22.8 4.5,23 5,23H18.96C19.5,23 19.96,22.8 20.37,22.39C20.77,22 21,21.5 21,21V7C21,6.46 20.77,6 20.37,5.61C19.96,5.22 19.5,5.03 18.96,5.03H16L12,1L7.96,5.03H5Z";var Z2="M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z";var s2="M4,6H20V16H4M20,18A2,2 0 0,0 22,16V6C22,4.89 21.1,4 20,4H4C2.89,4 2,4.89 2,6V16A2,2 0 0,0 4,18H0V20H24V18H20Z";var u2="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z";var S2="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z";var c2="M2,10.96C1.5,10.68 1.35,10.07 1.63,9.59L3.13,7C3.24,6.8 3.41,6.66 3.6,6.58L11.43,2.18C11.59,2.06 11.79,2 12,2C12.21,2 12.41,2.06 12.57,2.18L20.47,6.62C20.66,6.72 20.82,6.88 20.91,7.08L22.36,9.6C22.64,10.08 22.47,10.69 22,10.96L21,11.54V16.5C21,16.88 20.79,17.21 20.47,17.38L12.57,21.82C12.41,21.94 12.21,22 12,22C11.79,22 11.59,21.94 11.43,21.82L3.53,17.38C3.21,17.21 3,16.88 3,16.5V10.96C2.7,11.13 2.32,11.14 2,10.96M12,4.15V4.15L12,10.85V10.85L17.96,7.5L12,4.15M5,15.91L11,19.29V12.58L5,9.21V15.91M19,15.91V12.69L14,15.59C13.67,15.77 13.3,15.76 13,15.6V19.29L19,15.91M13.85,13.36L20.13,9.73L19.55,8.72L13.27,12.35L13.85,13.36Z",s1="M21,16.5C21,16.88 20.79,17.21 20.47,17.38L12.57,21.82C12.41,21.94 12.21,22 12,22C11.79,22 11.59,21.94 11.43,21.82L3.53,17.38C3.21,17.21 3,16.88 3,16.5V7.5C3,7.12 3.21,6.79 3.53,6.62L11.43,2.18C11.59,2.06 11.79,2 12,2C12.21,2 12.41,2.06 12.57,2.18L20.47,6.62C20.79,6.79 21,7.12 21,7.5V16.5M12,4.15L10.11,5.22L16,8.61L17.96,7.5L12,4.15M6.04,7.5L12,10.85L13.96,9.75L8.08,6.35L6.04,7.5M5,15.91L11,19.29V12.58L5,9.21V15.91M19,15.91V9.21L13,12.58V19.29L19,15.91Z",h2="M12 2C11.8 2 11.6 2.1 11.4 2.2L3.5 6.6C3.2 6.8 3 7.1 3 7.5V16.5C3 16.9 3.2 17.2 3.5 17.4L11.4 21.8C11.6 21.9 11.8 22 12 22S12.4 21.9 12.6 21.8L13.5 21.3C13.2 20.7 13.1 20 13 19.3V12.6L19 9.2V13C19.7 13 20.4 13.1 21 13.3V7.5C21 7.1 20.8 6.8 20.5 6.6L12.6 2.2C12.4 2.1 12.2 2 12 2M12 4.2L18 7.5L16 8.6L10.1 5.2L12 4.2M8.1 6.3L14 9.8L12 10.9L6 7.5L8.1 6.3M5 9.2L11 12.6V19.3L5 15.9V9.2M21.3 15.8L17.7 19.4L16.1 17.8L15 19L17.8 22L22.6 17.2L21.3 15.8Z";var O2="M8.35,3C9.53,2.83 10.78,4.12 11.14,5.9C11.5,7.67 10.85,9.25 9.67,9.43C8.5,9.61 7.24,8.32 6.87,6.54C6.5,4.77 7.17,3.19 8.35,3M15.5,3C16.69,3.19 17.35,4.77 17,6.54C16.62,8.32 15.37,9.61 14.19,9.43C13,9.25 12.35,7.67 12.72,5.9C13.08,4.12 14.33,2.83 15.5,3M3,7.6C4.14,7.11 5.69,8 6.5,9.55C7.26,11.13 7,12.79 5.87,13.28C4.74,13.77 3.2,12.89 2.41,11.32C1.62,9.75 1.9,8.08 3,7.6M21,7.6C22.1,8.08 22.38,9.75 21.59,11.32C20.8,12.89 19.26,13.77 18.13,13.28C17,12.79 16.74,11.13 17.5,9.55C18.31,8 19.86,7.11 21,7.6M19.33,18.38C19.37,19.32 18.65,20.36 17.79,20.75C16,21.57 13.88,19.87 11.89,19.87C9.9,19.87 7.76,21.64 6,20.75C5,20.26 4.31,18.96 4.44,17.88C4.62,16.39 6.41,15.59 7.47,14.5C8.88,13.09 9.88,10.44 11.89,10.44C13.89,10.44 14.95,13.05 16.3,14.5C17.41,15.72 19.26,16.75 19.33,18.38Z";var g2="M4.22,11.29L11.29,4.22C13.64,1.88 17.43,1.88 19.78,4.22C22.12,6.56 22.12,10.36 19.78,12.71L12.71,19.78C10.36,22.12 6.56,22.12 4.22,19.78C1.88,17.43 1.88,13.64 4.22,11.29M5.64,12.71C4.59,13.75 4.24,15.24 4.6,16.57L10.59,10.59L14.83,14.83L18.36,11.29C19.93,9.73 19.93,7.2 18.36,5.64C16.8,4.07 14.27,4.07 12.71,5.64L5.64,12.71Z";var f2="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z";var k2="M19 19C19 20.11 18.11 21 17 21H7C5.9 21 5 20.11 5 19V12H3V10H21V12H19M8 1.5C6.15 1.5 4.65 3 4.65 4.85C4.65 6.7 6.15 8.2 8 8.2H9.53C9.92 8.2 10.29 8.3 10.61 8.5H12.63C12.05 7.45 10.86 6.75 9.53 6.75H8C7 6.75 6.15 5.77 6.15 4.75C6.15 3.73 7 3 8 3M12.85 2C12.85 3 12 3.85 11 3.85V5.35C12.92 5.35 14.5 6.7 14.89 8.5H16.42C16.12 6.67 14.96 5.15 13.35 4.38C13.97 3.77 14.35 2.93 14.35 2Z";var b2="M16 7V3H14V7H10V3H8V7C7 7 6 8 6 9V14.5L9.5 18V21H14.5V18L18 14.5V9C18 8 17 7 16 7M16 13.67L13.09 16.59L12.67 17H11.33L10.92 16.59L8 13.67V9.09C8 9.06 8.06 9 8.09 9H15.92C15.95 9 16 9.06 16 9.09V13.67Z";var y2="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";var w2="M11,13.5V21.5H3V13.5H11M9,15.5H5V19.5H9V15.5M12,2L17.5,11H6.5L12,2M12,5.86L10.08,9H13.92L12,5.86M17.5,13C20,13 22,15 22,17.5C22,20 20,22 17.5,22C15,22 13,20 13,17.5C13,15 15,13 17.5,13M17.5,15A2.5,2.5 0 0,0 15,17.5A2.5,2.5 0 0,0 17.5,20A2.5,2.5 0 0,0 20,17.5A2.5,2.5 0 0,0 17.5,15Z";var B2="M2 15C2 15 2 12 4 12C4.68 12 5.46 11.95 6.28 11.82C7.2 12.54 8.5 13 10 13H10.25L8.56 11.29C8.91 11.18 9.25 11.05 9.59 10.91L11.5 12.82C11.89 12.74 12.25 12.63 12.58 12.5L10.55 10.45C10.85 10.28 11.14 10.11 11.43 9.91L13.5 12C13.8 11.79 14.04 11.56 14.25 11.32L12.22 9.29C12.46 9.07 12.7 8.83 12.92 8.58L14.79 10.45C14.91 10.14 15 9.83 15 9.5C15 8.65 14.55 7.89 13.84 7.28C13.89 7.19 13.95 7.1 14 7L15.53 6.23C16.38 7.17 18.14 7.84 20.25 7.97L20.3 8H21C21 8 22 9 22 12.5C22 13.07 22 13.57 21.96 14H19C17.9 14 16.58 14.26 15.3 14.5C14.12 14.76 12.9 15 12 15H2M21 17C21 17 21.58 17 21.86 15H19C17 15 14 16 12 16H2.28C2.62 16.6 3.26 17 4 17H21Z";var P2="M2,22V20C2,20 7,18 12,18C17,18 22,20 22,20V22H2M11.3,9.1C10.1,5.2 4,6.1 4,6.1C4,6.1 4.2,13.9 9.9,12.7C9.5,9.8 8,9 8,9C10.8,9 11,12.4 11,12.4V17C11.3,17 11.7,17 12,17C12.3,17 12.7,17 13,17V12.8C13,12.8 13,8.9 16,7.9C16,7.9 14,10.9 14,12.9C21,13.6 21,4 21,4C21,4 12.1,3 11.3,9.1Z";var T2="M5.06 3C4.63 3 4.22 3.14 3.84 3.42S3.24 4.06 3.14 4.5L2.11 8.91C1.86 10 2.06 10.95 2.72 11.77L3 12.05V19C3 19.5 3.2 20 3.61 20.39S4.5 21 5 21H19C19.5 21 20 20.8 20.39 20.39S21 19.5 21 19V12.05L21.28 11.77C21.94 10.95 22.14 10 21.89 8.91L20.86 4.5C20.73 4.06 20.5 3.7 20.13 3.42C19.77 3.14 19.38 3 18.94 3H5.06M18.89 4.97L19.97 9.38C20.06 9.81 19.97 10.2 19.69 10.55C19.44 10.86 19.13 11 18.75 11C18.44 11 18.17 10.9 17.95 10.66C17.73 10.43 17.61 10.16 17.58 9.84L16.97 5L18.89 4.97M5.06 5H7.03L6.42 9.84C6.3 10.63 5.91 11 5.25 11C4.84 11 4.53 10.86 4.31 10.55C4.03 10.2 3.94 9.81 4.03 9.38L5.06 5M9.05 5H11V9.7C11 10.05 10.89 10.35 10.64 10.62C10.39 10.88 10.08 11 9.7 11C9.36 11 9.07 10.88 8.84 10.59S8.5 10 8.5 9.66V9.5L9.05 5M13 5H14.95L15.5 9.5C15.58 9.92 15.5 10.27 15.21 10.57C14.95 10.87 14.61 11 14.2 11C13.89 11 13.61 10.88 13.36 10.62C13.11 10.35 13 10.05 13 9.7V5M7.45 12.05C8.08 12.67 8.86 13 9.8 13C10.64 13 11.38 12.67 12 12.05C12.69 12.67 13.45 13 14.3 13C15.17 13 15.92 12.67 16.55 12.05C17.11 12.67 17.86 13 18.8 13H19.03V19H5V13H5.25C6.16 13 6.89 12.67 7.45 12.05Z";var F2="M4,19H20V21H4V19M20,8V5H18V8H20M20,3C20.6,3 21,3.2 21.4,3.6C21.8,4 22,4.5 22,5V8C22,8.6 21.8,9 21.4,9.4C21,9.8 20.6,10 20,10H18V13C18,14.1 17.6,15 16.8,15.8C16,16.6 15.1,17 14,17H8C6.9,17 6,16.6 5.2,15.8C4.4,15 4,14.1 4,13V3H9V5.4L7.2,6.8C7.1,6.9 7,7.1 7,7.2V11.5C7,11.8 7.2,12 7.5,12H11.5C11.8,12 12,11.8 12,11.5V7.2C12,7 11.9,6.9 11.8,6.8L10,5.4V3H20Z";var R2="M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z";var D2="M6,2V8H6V8L10,12L6,16V16H6V22H18V16H18V16L14,12L18,8V8H18V2H6M16,16.5V20H8V16.5L12,12.5L16,16.5M12,11.5L8,7.5V4H16V7.5L12,11.5Z";var E2="M19 6V5A2 2 0 0 0 17 3H15A2 2 0 0 0 13 5V6H11V5A2 2 0 0 0 9 3H7A2 2 0 0 0 5 5V6H3V20H21V6Z";var _2="M3,13.5L2.25,12H7.5L6.9,10.5H2L1.25,9H9.05L8.45,7.5H1.11L0.25,6H4A2,2 0 0,1 6,4H18V8H21L24,12V17H22A3,3 0 0,1 19,20A3,3 0 0,1 16,17H12A3,3 0 0,1 9,20A3,3 0 0,1 6,17H4V13.5H3M19,18.5A1.5,1.5 0 0,0 20.5,17A1.5,1.5 0 0,0 19,15.5A1.5,1.5 0 0,0 17.5,17A1.5,1.5 0 0,0 19,18.5M20.5,9.5H18V12H22.46L20.5,9.5M9,18.5A1.5,1.5 0 0,0 10.5,17A1.5,1.5 0 0,0 9,15.5A1.5,1.5 0 0,0 7.5,17A1.5,1.5 0 0,0 9,18.5Z",$2="M.75 7.5H10.5L11.25 9H1.5L.75 7.5M1.75 10.5H11.5L12.25 12H2.5L1.75 10.5M18 18.5C18.83 18.5 19.5 17.83 19.5 17C19.5 16.17 18.83 15.5 18 15.5C17.17 15.5 16.5 16.17 16.5 17C16.5 17.83 17.17 18.5 18 18.5M19.5 9.5H17V12H21.46L19.5 9.5M8 18.5C8.83 18.5 9.5 17.83 9.5 17C9.5 16.17 8.83 15.5 8 15.5C7.17 15.5 6.5 16.17 6.5 17C6.5 17.83 7.17 18.5 8 18.5M20 8L23 12V17H21C21 18.66 19.66 20 18 20C16.34 20 15 18.66 15 17H11C11 18.66 9.65 20 8 20C6.34 20 5 18.66 5 17H3V13.5 13.5H5V15H5.76C6.31 14.39 7.11 14 8 14C8.89 14 9.69 14.39 10.24 15H15V6H3V6C3 4.89 3.89 4 5 4H17V8H20Z";var N2="M18 18.5C18.83 18.5 19.5 17.83 19.5 17C19.5 16.17 18.83 15.5 18 15.5C17.17 15.5 16.5 16.17 16.5 17C16.5 17.83 17.17 18.5 18 18.5M19.5 9.5H17V12H21.46L19.5 9.5M6 18.5C6.83 18.5 7.5 17.83 7.5 17C7.5 16.17 6.83 15.5 6 15.5C5.17 15.5 4.5 16.17 4.5 17C4.5 17.83 5.17 18.5 6 18.5M20 8L23 12V17H21C21 18.66 19.66 20 18 20C16.34 20 15 18.66 15 17H9C9 18.66 7.66 20 6 20C4.34 20 3 18.66 3 17H1V6C1 4.89 1.89 4 3 4H17V8H20M3 6V15H3.76C4.31 14.39 5.11 14 6 14C6.89 14 7.69 14.39 8.24 15H15V6H3Z";var W2="M16,21H8A1,1 0 0,1 7,20V12.07L5.7,13.07C5.31,13.46 4.68,13.46 4.29,13.07L1.46,10.29C1.07,9.9 1.07,9.27 1.46,8.88L7.34,3H9C9,4.1 10.34,5 12,5C13.66,5 15,4.1 15,3H16.66L22.54,8.88C22.93,9.27 22.93,9.9 22.54,10.29L19.71,13.12C19.32,13.5 18.69,13.5 18.3,13.12L17,12.12V20A1,1 0 0,1 16,21";var I2="M6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18A6,6 0 0,1 6,12M20,12C20,9.45 18.81,7.19 16.95,5.73L16,0H8L7.05,5.73C5.19,7.19 4,9.45 4,12C4,14.54 5.19,16.81 7.05,18.27L8,24H16L16.95,18.27C18.81,16.81 20,14.54 20,12Z";var U2="M12,3.77L11.25,4.61C11.25,4.61 9.97,6.06 8.68,7.94C7.39,9.82 6,12.07 6,14.23A6,6 0 0,0 12,20.23A6,6 0 0,0 18,14.23C18,12.07 16.61,9.82 15.32,7.94C14.03,6.06 12.75,4.61 12.75,4.61L12,3.77M12,6.9C12.44,7.42 12.84,7.85 13.68,9.07C14.89,10.83 16,13.07 16,14.23C16,16.45 14.22,18.23 12,18.23C9.78,18.23 8,16.45 8,14.23C8,13.07 9.11,10.83 10.32,9.07C11.16,7.85 11.56,7.42 12,6.9Z";var v={alert:G1,warn:Q1,check:X1,checkCircle:Y1,chevronDown:J1,chevronRight:C2,close:L2,copy:r2,delete:e2,info:Z2,menu:S2,more:i2,plus:f2,refresh:y2,search:u2,shape:w2,empty:c2,truckNow:_2,labelCreated:H2,inTransit:N2,outForDelivery:$2,pickup:T2,delivered:h2,home:x2,missed:l2,stalled:V2,notFound:n2,waiting:D2},k5={"mdi:package-variant-closed":s1,"mdi:coffee":M2,"mdi:tea":F2,"mdi:shoe-sneaker":B2,"mdi:desk-lamp":t2,"mdi:power-plug-outline":b2,"mdi:book-open-page-variant":K1,"mdi:laptop":s2,"mdi:cellphone":j1,"mdi:headphones":m2,"mdi:camera":q1,"mdi:image-frame":v2,"mdi:sprout":P2,"mdi:pill":g2,"mdi:tshirt-crew":W2,"mdi:water-outline":U2,"mdi:toy-brick":E2,"mdi:gamepad-variant":a2,"mdi:gift":A2,"mdi:watch":I2,"mdi:paw":O2,"mdi:hammer-wrench":d2,"mdi:pot-steam":k2,"mdi:glass-wine":p2,"mdi:food-apple":o2,"mdi:television":R2,"mdi:battery-charging":z1},Q={"mdi:package-variant-closed":"Box","mdi:gift":"Gift","mdi:tshirt-crew":"Clothes","mdi:shoe-sneaker":"Shoes","mdi:book-open-page-variant":"Book","mdi:cellphone":"Phone","mdi:laptop":"Computer","mdi:headphones":"Audio","mdi:camera":"Camera","mdi:coffee":"Coffee","mdi:pot-steam":"Kitchen","mdi:sprout":"Garden","mdi:pill":"Health","mdi:toy-brick":"Toys","mdi:paw":"Pets","mdi:hammer-wrench":"Tools","mdi:image-frame":"Art","mdi:desk-lamp":"Lamp","mdi:power-plug-outline":"Electrical","mdi:tea":"Tea","mdi:water-outline":"Water","mdi:gamepad-variant":"Games","mdi:watch":"Watch","mdi:glass-wine":"Wine","mdi:food-apple":"Food","mdi:television":"TV","mdi:battery-charging":"Battery"},G2=L=>k5[L]||s1;var Q2={delivered:{key:"delivered",label:"Delivered",icon:"delivered",color:"--st-delivered",stage:3},stalled:{key:"stalled",label:"No recent updates",icon:"stalled",color:"--st-muted",stage:1,attn:!0},in_transit:{key:"transit",label:"On the way",icon:"inTransit",color:"--st-transit",stage:1},ready_for_pickup:{key:"pickup",label:"Ready for pickup",icon:"pickup",color:"--st-pickup",stage:2},out_for_delivery:{key:"out",label:"Out for delivery",icon:"outForDelivery",color:"--st-out",stage:2},not_found:{key:"notfound",label:"Not found yet",icon:"notFound",color:"--st-muted",stage:0},failed_attempt:{key:"failed",label:"Missed delivery",icon:"missed",color:"--st-failed",stage:2,attn:!0},exception:{key:"exception",label:"Delivery problem",icon:"alert",color:"--st-attention",stage:1,attn:!0},label_created:{key:"pre",label:"Label created",icon:"labelCreated",color:"--st-pre",stage:0}},b5={key:"pending",label:"Waiting for first update",icon:"waiting",color:"--st-muted",stage:-1},H1=[{label:"Label created",icon:"labelCreated"},{label:"On the way",icon:"inTransit"},{label:"Out for delivery",icon:"outForDelivery"},{label:"Delivered",icon:"home"}],K2=[H1[0],H1[1],{label:"Ready for pickup",icon:"pickup"},{label:"Picked up",icon:"delivered"}],q2={new:{title:"Just added"},pickup:{title:"Ready for pickup",sub:()=>"Waiting for you"},today:{title:"Today",sub:L=>L.fmt.longDate(L.today)},late:{title:"Running late",sub:()=>"Expected earlier"},tomorrow:{title:"Tomorrow",sub:L=>L.fmt.longDate(J(L.today,1))},week:{title:"Later this week"},later:{title:"Coming later"},nodate:{title:"No delivery date yet"},delivered:{title:"Delivered"}},V1=["new","pickup","today","late","tomorrow","week","later","nodate","delivered"],z2=["new","late","tomorrow","week","later","nodate"],u1={1:{label:"Postcode",type:"text",placeholder:"Destination postcode",autocomplete:"postal-code"},2:{label:"Email used for the order",type:"email",placeholder:"you@example.com",autocomplete:"email",number:"Order number"},3:{label:"PIN",type:"text",placeholder:"PIN from the shipping notice",autocomplete:"off"},4:{label:"Phone number",type:"tel",placeholder:"Phone number on the order",autocomplete:"tel"},5:{label:"Country code and postcode",type:"text",placeholder:"US12345",autocomplete:"off"}},y5="mdi:package-variant-closed",w5=700,B5=56,P5=34,S1=L=>L&&L.charAt(0).toUpperCase()+L.slice(1),T5=(L,C)=>`${L} ${C}${L===1?"":"s"}`,j2=L=>L.replace(/[\s-]/g,"").toUpperCase();function X2(L){let C=[];for(let H of L?.entries||[]){let V={entryId:H.entry_id,entryTitle:H.title,canDelete:H.can_delete};for(let M of H.deliveries||[])C.push({...V,uid:`${H.entry_id}|${M.key}`,key:M.key,pending:!1,description:M.description,trackingNumber:M.tracking_number,carrierCode:M.carrier_code,carrierName:M.carrier_name,carrierShort:M.carrier_short,status:M.status,etaStart:S(M.eta_start),etaEnd:S(M.eta_end),etaDate:M.eta_date||null,deliveredAt:S(M.delivered_at),events:(M.events||[]).map(r=>({text:r.event,when:S(r.date),whenText:r.date_text,location:r.location,additional:r.additional})),icon:M.icon,iconSource:M.icon_source});for(let M of H.pending||[])C.push({...V,uid:`${H.entry_id}|${M.key}`,key:M.key,pending:!0,description:M.description,trackingNumber:M.tracking_number,carrierCode:M.carrier_code,carrierName:M.carrier_name,carrierShort:M.carrier_short,status:null,etaStart:null,etaEnd:null,etaDate:null,deliveredAt:null,events:[],icon:M.icon,iconSource:M.icon_source,addedAt:S(M.added_at)})}return C}var O=L=>L.pending?b5:Q2[L.status]||Q2.not_found;function z(L,C){if(L.etaDate)return L.etaDate;let H=L.etaStart||L.etaEnd;return H?C.ymd(H):null}function C1(L){return L.etaStart||L.etaEnd?(L.etaStart||L.etaEnd).getTime():L.etaDate?Date.parse(`${L.etaDate}T00:00:00`):1/0}function F5(L,C,H){if(L.pending)return"new";let V=O(L);if(V.key==="delivered")return"delivered";if(V.attn)return"attention";if(V.key==="pickup")return"pickup";let M=z(L,H);if(V.key==="out"||M===C)return"today";if(!M)return"nodate";let r=G(C,M);return r<0?"late":r===1?"tomorrow":r<6?"week":"later"}function Y2(L,C,H){let V={attention:[]};for(let M of V1)V[M]=[];for(let M of L)V[F5(M,C,H)].push(M);for(let M of V1)M==="delivered"?V[M].sort((r,e)=>(e.deliveredAt?.getTime()||0)-(r.deliveredAt?.getTime()||0)):V[M].sort((r,e)=>C1(r)-C1(e));return V.attention.sort((M,r)=>C1(M)-C1(r)),V}function J2(L,C){let H=C.trim().toLowerCase();if(!H)return!0;let V=H.replace(/[\s-]/g,"");return L.description.toLowerCase().includes(H)||V.length>0&&L.trackingNumber.toLowerCase().includes(V)||(L.carrierName||"").toLowerCase().includes(H)}function C5(L,C){for(let H of L)if(H.re.test(C||""))return H.icon;return y5}function c1(L,C="i"){return(L||[]).flatMap(H=>{try{return[{...H,re:new RegExp(H.pattern,C)}]}catch{return[]}})}function T(L,C,H,V=!0){return C===H?"today":C===J(H,1)?"tomorrow":C===J(H,-1)?"yesterday":Math.abs(G(H,C))<6?L.weekday(C,V?"long":"short"):L.shortDate(C)}var H5=(L,C,H)=>`${S1(T(L,L.ymd(C),H,!1))}, ${L.time(C)}`;function L1(L,C){let H=Math.round((C-L)/6e4);if(H<1)return"just now";if(H<60)return`${H} min ago`;let V=Math.round(H/60);if(V<24)return`${V} hr ago`;let M=Math.round(V/24);return M===1?"yesterday":`${M} days ago`}function R5(L,C){let H=Math.round((L-C)/6e4);if(H<=0)return"";if(H<50)return`In about ${Math.max(5,Math.round(H/5)*5)} minutes`;let V=Math.round(H/60);return V===1?"In about an hour":`In about ${V} hours`}function h1(L,C,H){let V=L.events[0],M=L.carrierShort||L.carrierName;if(C.key==="failed"){let r=z(L,H.fmt),e=r?`${M} will try again ${T(H.fmt,r,H.today)}${L.etaStart&&L.etaEnd?`, ${H.fmt.window(L.etaStart,L.etaEnd)}`:""}.`:`Check with ${M} about the next attempt.`;return{title:"Missed delivery",hint:`${V?.additional?`${V.additional.split(". ")[0].replace(/\.$/,"")}. `:""}${e}`}}return C.key==="exception"?{title:V?.text||"Delivery problem",hint:V?.additional||`Check with ${M} for details.`}:C.key==="stalled"?{title:"No updates for a while",hint:V?.when?`Last update ${L1(V.when,H.now)}.`:`Check with ${M} if it seems late.`}:{title:C.label,hint:""}}function V5(L,C,H){let{fmt:V,today:M}=H;if(L.pending)return{main:"New",sub:"just added"};if(C.key==="delivered"){if(!L.deliveredAt)return{main:"Delivered",sub:""};let t=V.ymd(L.deliveredAt);return t===M?{main:V.time(L.deliveredAt),sub:"today"}:{main:S1(T(V,t,M,!1)),sub:V.time(L.deliveredAt)}}if(C.key==="pickup")return{main:"Pick up",sub:"ready now"};let r=z(L,V);if(!r)return{main:"\u2014",sub:"no date yet"};let e=L.etaStart&&L.etaEnd?V.window(L.etaStart,L.etaEnd):L.etaEnd?`by ${V.time(L.etaEnd)}`:"",i=G(M,r);return i===0?{main:e||"Today",sub:e?"today":"any time"}:i<0?{main:"Late",sub:`was due ${V.monthDay(r)}`}:i===1?{main:"Tomorrow",sub:e}:i<6?{main:V.weekday(r,"short"),sub:V.monthDay(r)}:{main:V.monthDay(r),sub:V.weekday(r,"short")}}function L5(L,C){let H=L.events[0],V=[L.carrierShort||L.carrierName];return L.pending?V.push("Parcel will check in a few minutes"):H?.location?V.push(H.location):H?.text&&H.text.toLowerCase()!==O(L).label.toLowerCase()&&V.push(H.text),!L.pending&&H?.when&&V.push(L1(H.when,C.now)),V.filter(Boolean).join(" \xB7 ")}function M5(L,C,H){let{fmt:V,today:M,now:r}=H;if(L.pending)return{main:"Waiting for the first update",sub:"Parcel will check with the carrier in a few minutes."};if(C.key==="delivered"){if(!L.deliveredAt)return{main:"Delivered",sub:L.events[0]?.location||""};let n=L.events[0]?.location;return{main:`Delivered ${T(V,V.ymd(L.deliveredAt),M)}`,sub:`At ${V.time(L.deliveredAt)}${n?` \xB7 ${n}`:""}`,note:L.events[0]?.additional||""}}if(C.key==="pickup")return{main:"Ready for pickup",sub:L.events[0]?.location||"",note:L.events[0]?.additional||""};if(C.attn){let n=h1(L,C,H);return{main:n.title,sub:n.hint}}let e=z(L,V);if(!e)return{main:"No delivery date yet",sub:"The carrier hasn\u2019t shared an estimate."};let i="";L.etaStart&&L.etaEnd?i=S1(V.between(L.etaStart,L.etaEnd)):L.etaEnd?i=`By ${V.time(L.etaEnd)}`:C.key==="pre"?i="The carrier doesn\u2019t have the package yet.":e===M&&(i="No time window from the carrier.");let t="";L.etaStart&&V.ymd(L.etaStart)===M&&(t=L.etaStart<=r&&(!L.etaEnd||r<=L.etaEnd)?"Could arrive any minute":R5(L.etaStart,r));let p=G(M,e)<0;return{main:p?`Expected ${T(V,e,M)}`:`Arriving ${T(V,e,M)}`,sub:p?"Running late. The carrier hasn\u2019t updated the date.":i,note:t}}function r5(L,C){let{fmt:H,today:V}=C,M=L.today,r=L.delivered.filter(d=>d.deliveredAt&&H.ymd(d.deliveredAt)===V),e=z2.reduce((d,a)=>d+L[a].length,0),i,t,p="--st-out";if(M.length){i="today";let d=M.filter(m=>m.etaStart).map(m=>m.etaStart.getTime()),a=M.filter(m=>m.etaEnd||m.etaStart).map(m=>(m.etaEnd||m.etaStart).getTime());d.length&&a.length?t=`Expected ${H.between(new Date(Math.min(...d)),new Date(Math.max(...a)))}.`:a.length?t=`Expected by ${H.time(new Date(Math.max(...a)))}.`:t="The carriers haven\u2019t shared delivery times yet.",r.length&&(t+=` ${r.length} already delivered today.`)}else if(r.length)i="delivered",p="--st-delivered",t=`${T5(r.length,"package")} delivered today.`;else{i="none",p="--st-transit";let d=[...L.tomorrow,...L.week,...L.later][0];t=d?`Next up: ${d.description}, ${T(H,z(d,H),V)}.`:"Your packages are on their way."}let n=[];return L.attention.length&&n.push({n:L.attention.length,label:L.attention.length===1?"needs a look":"need a look",color:"--st-attention",target:"sec-attention"}),L.pickup.length&&n.push({n:L.pickup.length,label:"to pick up",color:"--st-pickup",target:"sec-pickup"}),e&&n.push({n:e,label:"coming later",color:"--st-transit",target:`sec-${z2.find(d=>L[d].length)}`}),r.length&&n.push({n:r.length,label:"delivered today",color:"--st-delivered",target:"sec-delivered"}),{kind:i,count:M.length,sub:t,color:p,stats:n,todays:M,deliveredToday:r}}function e5(L,C,H){let{fmt:V,today:M,now:r}=H,e=V.hours(r),i=o=>{let u=V.ymd(o);return u<M?0:u>M?24:V.hours(o)},t=[],p=[];for(let o of L){if(!o.etaStart&&!o.etaEnd){p.push(o);continue}let u=o.etaEnd?i(o.etaEnd):Math.min(24,i(o.etaStart)+2),F=o.etaStart?i(o.etaStart):Math.min(e,u-.5);F>u-.25&&(F=Math.max(0,u-.5));let p5=o.etaStart&&o.etaEnd?V.window(o.etaStart,o.etaEnd):o.etaEnd?`by ${V.time(o.etaEnd)}`:`from ${V.time(o.etaStart)}`;t.push({d:o,st:O(o),start:F,end:u,at:(F+u)/2,label:p5,done:!1})}for(let o of C){let u=V.hours(o.deliveredAt);t.push({d:o,st:O(o),start:u,end:u,at:u,label:`delivered ${V.time(o.deliveredAt)}`,done:!0})}if(!t.length&&!p.length)return null;let n=8,d=20;for(let o of t)n=Math.min(n,Math.floor(o.start)),d=Math.max(d,Math.ceil(o.end));n=Math.max(0,Math.min(n,Math.floor(e))),d=Math.min(24,Math.max(d,Math.ceil(e))),(d-n)%2&&(d<24?d+=1:n-=1);let a=o=>Math.min(100,Math.max(0,(o-n)/(d-n)*100));t.sort((o,u)=>o.at-u.at);let m=[],x=(d-n)*.075;for(let o of t){let u=m.findIndex(F=>o.at-F>=x);u===-1&&(u=m.length<3?m.length:m.indexOf(Math.min(...m))),m[u]=o.at,o.lane=u,o.x=a(o.at)}let s=(H.roadWidth||w5)/(d-n),c=[2,4,6,8,12].find(o=>o*s>=B5)||12,g=[];for(let o=n;o<=d;o+=2){let u=(o-n)%c!==0||Math.abs(o-e)*s<P5;g.push({hour:o,left:a(o),label:V.hourLabel(o),hidden:u})}return{pins:t,anytime:p,ticks:g,from:n,to:d,lanes:Math.max(1,m.length),nowLeft:a(e),bands:t.filter(o=>!o.done).map(o=>({left:a(o.start),width:Math.max(a(o.end)-a(o.start),1.5),color:o.st.color}))}}function t5(L,C){if(!L)return[];let H=L.list;return[...new Set(L.detect.filter(V=>V.re.test(C)).map(V=>V.code))].filter(V=>H[V])}function i5(L,C,H){let V=L?.list||{},M=C.trim().toLowerCase(),r=Object.entries(V).map(([t,p])=>({code:t,name:p.name}));if(!M){let t=[...H,...(L?.suggested||[]).filter(a=>!H.includes(a))].filter(a=>V[a]),p=t.map((a,m)=>({code:a,name:V[a].name,heading:m===0?H.length?"Suggested":"Common":""})),n=r.filter(a=>!t.includes(a.code)).sort((a,m)=>a.name.localeCompare(m.name)),d=n.slice(0,40).map((a,m)=>({...a,heading:m===0?"All carriers":""}));return{items:[...p,...d],more:Math.max(0,n.length-40)}}let e=t=>t.name.toLowerCase().startsWith(M)?0:1,i=r.filter(t=>t.name.toLowerCase().includes(M)||t.code.includes(M)).sort((t,p)=>e(t)-e(p)||t.name.localeCompare(p.name));return{items:i.slice(0,50),more:Math.max(0,i.length-50)}}var o5='button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';function a5(L,C,H){if(!L.length)return null;let V=L[0],M=L[L.length-1];return L.includes(C)?H&&C===V?M:!H&&C===M?V:null:H?M:V}var A5=e1`
  :host {
    --pp-primary: var(--primary-color, #03a9f4);
    --pp-on-primary: var(--text-primary-color, #ffffff);
    --pp-bg: var(--primary-background-color, #fafafa);
    --pp-card: var(--card-background-color, var(--ha-card-background, #ffffff));
    --pp-text: var(--primary-text-color, #212121);
    --pp-text2: var(--secondary-text-color, #727272);
    --pp-text3: var(--disabled-text-color, #a0a0a0);
    --pp-line: var(--divider-color, rgba(0, 0, 0, 0.12));
    --pp-surface: var(--secondary-background-color, #e5e5e5);
    --pp-surface2: color-mix(in srgb, var(--pp-text) 4%, var(--pp-card));
    --pp-card-line: color-mix(in srgb, var(--pp-text) 9%, var(--pp-card));
    --pp-ring-off: color-mix(in srgb, var(--pp-text) 12%, var(--pp-card));
    --pp-road: color-mix(in srgb, var(--pp-text) 9%, var(--pp-card));
    --pp-road-dash: var(--pp-card);
    --pp-hover: color-mix(in srgb, var(--pp-text) 7%, transparent);
    --pp-selected: color-mix(in srgb, var(--pp-primary) 12%, var(--pp-card));
    --pp-disabled-bg: color-mix(in srgb, var(--pp-text) 10%, transparent);
    --pp-input-bg: color-mix(in srgb, var(--pp-text) 3%, var(--pp-card));
    --pp-input-line: color-mix(in srgb, var(--pp-text) 22%, var(--pp-card));
    --pp-switch-off: color-mix(in srgb, var(--pp-text) 25%, var(--pp-card));
    --pp-hero-top: color-mix(in srgb, var(--pp-primary) 10%, var(--pp-card));
    --pp-scrim: rgba(0, 0, 0, 0.42);
    --pp-toast-bg: var(--pp-text);
    --pp-toast-fg: var(--pp-card);
    --pp-danger: var(--error-color, #db4437);
    --pp-on-danger: #ffffff;
    --pp-shadow-1: 0 1px 2px rgba(21, 27, 34, 0.05), 0 4px 14px rgba(21, 27, 34, 0.06);
    --pp-shadow-2: 0 2px 6px rgba(21, 27, 34, 0.07), 0 14px 32px rgba(21, 27, 34, 0.11);
    --st-pre: #5f6d7b;
    --st-transit: #4855d4;
    --st-out: #0b7a6e;
    --st-pickup: #8546d6;
    --st-failed: #c2410c;
    --st-attention: #d42a2a;
    --st-delivered: #237a3b;
    --st-muted: #6f7a85;
    --font-body: var(--ha-font-family-body, Roboto, 'Noto Sans', 'Helvetica Neue', Arial, sans-serif);
    --font-display: 'Parcel Outfit', var(--font-body);
    --font-mono: var(--ha-font-family-code, 'Roboto Mono', ui-monospace, Menlo, Consolas, monospace);
    --r-lg: 24px;
    --r-md: 18px;
    display: block;
    min-height: 100%;
    background: var(--pp-bg);
    color: var(--pp-text);
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.45;
    -webkit-font-smoothing: antialiased;
  }
  :host([dark]) {
    --pp-scrim: rgba(0, 0, 0, 0.58);
    --pp-shadow-1: 0 1px 2px rgba(0, 0, 0, 0.4), 0 4px 14px rgba(0, 0, 0, 0.25);
    --pp-shadow-2: 0 2px 6px rgba(0, 0, 0, 0.45), 0 14px 32px rgba(0, 0, 0, 0.4);
    --st-pre: #a3b3c2;
    --st-transit: #9aa6ff;
    --st-out: #52d6c4;
    --st-pickup: #c4a0ff;
    --st-failed: #ff9d5c;
    --st-attention: #ff7373;
    --st-delivered: #74d68e;
    --st-muted: #94a0ab;
  }
  * { box-sizing: border-box; }
  button, input, select { font: inherit; color: inherit; }
  button { cursor: pointer; }
  h1, h2, h3, p { margin: 0; }
  a { color: var(--pp-primary); }
  .ic { width: 24px; height: 24px; fill: currentColor; flex: none; }
  .ic.sm { width: 20px; height: 20px; }
  .ic.xs { width: 16px; height: 16px; }
  .ic.xxs { width: 12px; height: 12px; }
  :focus-visible { outline: 2px solid var(--pp-primary); outline-offset: 2px; }
  .muted { color: var(--pp-text2); }

  /* Top bar */
  .appbar {
    position: sticky; top: 0; z-index: 8;
    background: var(--app-header-background-color, var(--pp-bg));
    color: var(--app-header-text-color, var(--pp-text));
    border-bottom: var(--app-header-border-bottom, 1px solid var(--pp-line));
  }
  .appbar-inner { display: flex; align-items: center; gap: 4px; height: var(--header-height, 56px); padding: 0 12px 0 16px; }
  .appbar h1 { margin-left: 4px; font-size: 20px; font-weight: 400; white-space: nowrap; }
  .spacer { flex: 1; }
  .updated { margin-left: 6px; font-size: 12px; color: var(--pp-text2); white-space: nowrap; }
  .icon-btn {
    width: 40px; height: 40px; flex: none; display: inline-grid; place-items: center;
    border: 0; border-radius: 50%; background: none; color: inherit; opacity: 0.85;
  }
  .icon-btn:hover { background: var(--pp-hover); opacity: 1; }
  .icon-btn.tiny { width: 30px; height: 30px; color: var(--pp-text2); }
  .icon-btn.spin .ic { animation: spin 0.9s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .search {
    display: flex; align-items: center; gap: 6px; height: 40px; width: min(340px, 100%);
    padding: 0 4px 0 12px; border-radius: 999px; color: var(--pp-text2);
    background: var(--pp-card); box-shadow: var(--pp-shadow-1);
  }
  .search input { flex: 1; min-width: 0; border: 0; background: none; outline: none; color: var(--pp-text); font-size: 14px; }
  .search input::-webkit-search-cancel-button { display: none; }
  @media (max-width: 600px) {
    .updated { display: none; }
    .appbar.searching h1, .appbar.searching .spacer { display: none; }
    .appbar.searching .search { flex: 1; width: auto; }
  }

  /* Page */
  .main {
    max-width: 880px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px;
    padding: 24px 16px 132px; overflow-x: clip;
  }
  .banner {
    display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; border-radius: 14px;
    background: color-mix(in srgb, var(--st-failed) 9%, var(--pp-card)); color: var(--pp-text);
    border: 1px solid color-mix(in srgb, var(--st-failed) 25%, var(--pp-card-line));
  }
  .banner .ic { color: var(--st-failed); }
  .banner.info {
    background: color-mix(in srgb, var(--pp-primary) 8%, var(--pp-card));
    border-color: color-mix(in srgb, var(--pp-primary) 24%, var(--pp-card-line));
  }
  .banner.info .ic { color: var(--pp-primary); }
  .loading { padding: 64px 16px; text-align: center; color: var(--pp-text2); }

  /* Hero */
  .hero {
    position: relative; padding: 26px 26px 22px; border-radius: var(--r-lg);
    background: linear-gradient(180deg, var(--pp-hero-top), var(--pp-card) 72%);
    border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-1);
  }
  .hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
  .greet { font-size: 14px; font-weight: 500; color: var(--pp-text2); }
  .hero-h { margin-top: 6px; font: 600 clamp(28px, 5.2vw, 42px) / 1.06 var(--font-display); letter-spacing: -0.025em; text-wrap: balance; }
  .hero-h .n { color: var(--c, var(--pp-text)); }
  .hero-sub { margin-top: 10px; max-width: 46ch; font-size: 15px; color: var(--pp-text2); }
  .cal {
    flex: none; display: grid; justify-items: center; width: 74px; padding: 9px 0 10px; border-radius: 18px;
    background: var(--pp-card); border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-1);
  }
  .cal .dow { font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--pp-primary); }
  .cal .dom { margin-top: 4px; font: 600 32px / 1.05 var(--font-display); font-variant-numeric: tabular-nums; }
  .cal .mon { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--pp-text2); }
  @media (max-width: 560px) {
    .hero { padding: 20px 16px 18px; }
    .cal { display: none; }
  }
  .road-wrap { position: relative; margin-top: 22px; padding: 0 18px; }
  .pins { position: relative; height: calc(46px + (var(--lanes) - 1) * 40px); }
  .pin { position: absolute; bottom: 0; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; padding: 0; border: 0; background: none; }
  .pin-av {
    position: relative; width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center;
    background: color-mix(in srgb, var(--c) 16%, var(--pp-card)); color: var(--c);
    box-shadow: 0 0 0 3px var(--pp-card), var(--pp-shadow-1); transition: transform 0.15s ease;
  }
  .pin-av .ic { width: 20px; height: 20px; }
  .pin:hover .pin-av, .pin:focus-visible .pin-av { transform: translateY(-2px) scale(1.06); }
  .pin.done .pin-av { background: color-mix(in srgb, var(--st-delivered) 14%, var(--pp-card)); color: var(--st-delivered); }
  .pin-check {
    position: absolute; right: -4px; bottom: -4px; width: 16px; height: 16px; border-radius: 50%; display: grid; place-items: center;
    background: var(--st-delivered); color: var(--pp-card); box-shadow: 0 0 0 2px var(--pp-card);
  }
  .stem { width: 2px; height: calc(8px + var(--lane) * 40px); border-radius: 2px; background: color-mix(in srgb, var(--c) 45%, transparent); }
  .tip {
    position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%); z-index: 3;
    padding: 6px 10px; border-radius: 8px; white-space: nowrap; pointer-events: none;
    background: var(--pp-toast-bg); color: var(--pp-toast-fg); font-size: 12px; font-weight: 500; opacity: 0; transition: opacity 0.12s ease;
  }
  .pin.edge-l .tip { left: -8px; transform: none; }
  .pin.edge-r .tip { left: auto; right: -8px; transform: none; }
  .pin:hover .tip, .pin:focus-visible .tip { opacity: 1; }
  .road { position: relative; height: 14px; border-radius: 7px; background: var(--pp-road); }
  .road::after {
    content: ''; position: absolute; left: 10px; right: 10px; top: 6px; height: 2px;
    background: repeating-linear-gradient(to right, var(--pp-road-dash) 0 10px, transparent 10px 22px);
  }
  .band { position: absolute; top: 2px; bottom: 2px; border-radius: 5px; background: color-mix(in srgb, var(--c) 46%, transparent); }
  .now-truck {
    position: absolute; z-index: 2; top: 50%; transform: translate(-50%, -50%);
    width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
    background: var(--pp-primary); color: var(--pp-on-primary);
    box-shadow: 0 0 0 4px var(--pp-card), 0 0 0 9px color-mix(in srgb, var(--pp-primary) 18%, transparent);
  }
  .hours { position: relative; height: 18px; margin-top: 10px; font-size: 12px; color: var(--pp-text2); font-variant-numeric: tabular-nums; }
  .hours span { position: absolute; top: 0; transform: translateX(-50%); white-space: nowrap; }
  .hours .now-lab { color: var(--pp-primary); font-weight: 600; }
  .anytime { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 16px; }
  .any-label { margin-right: 2px; font-size: 13px; color: var(--pp-text2); }
  .any-chip {
    display: inline-flex; align-items: center; gap: 8px; max-width: 100%; min-width: 0; height: 36px; padding: 0 14px 0 4px; border-radius: 999px;
    border: 1px solid var(--pp-card-line); background: var(--pp-card); box-shadow: var(--pp-shadow-1); font-size: 13px; font-weight: 500;
  }
  .any-chip:hover { box-shadow: var(--pp-shadow-2); }
  .any-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .any-av { width: 28px; height: 28px; flex: none; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--c) 15%, var(--pp-card)); color: var(--c); }
  .hero-stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
  .stat {
    display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 14px 0 5px; border: 0; border-radius: 999px;
    background: color-mix(in srgb, var(--c) 11%, var(--pp-card)); color: var(--pp-text); font-size: 13px; font-weight: 500;
  }
  .stat:hover { background: color-mix(in srgb, var(--c) 18%, var(--pp-card)); }
  .stat .sn {
    min-width: 26px; height: 26px; padding: 0 7px; border-radius: 999px; display: grid; place-items: center;
    background: var(--c); color: var(--pp-card); font: 600 13px / 1 var(--font-display);
  }

  /* Needs a look */
  .attention {
    scroll-margin-top: 76px; padding: 18px 18px 8px; border-radius: var(--r-md);
    background: color-mix(in srgb, var(--st-attention) 6%, var(--pp-card));
    border: 1px solid color-mix(in srgb, var(--st-attention) 22%, var(--pp-card-line));
  }
  .att-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .att-ic { width: 40px; height: 40px; flex: none; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--st-attention) 14%, transparent); color: var(--st-attention); }
  .att-head h3 { font: 600 19px / 1.2 var(--font-display); letter-spacing: -0.01em; }
  .att-head p { margin-top: 2px; font-size: 13px; color: var(--pp-text2); }
  .att-row {
    display: grid; grid-template-columns: 44px minmax(0, 1fr) 20px; align-items: center; gap: 12px; width: 100%;
    padding: 12px 4px; border: 0; background: none; text-align: left;
    border-top: 1px solid color-mix(in srgb, var(--st-attention) 14%, var(--pp-line));
  }
  .att-row .chev { color: var(--pp-text2); }
  .att-row:hover .att-name { text-decoration: underline; }
  .att-av { width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--c) 14%, var(--pp-card)); color: var(--c); }
  .att-text { display: grid; gap: 2px; min-width: 0; }
  .att-name { font: 500 16px / 1.25 var(--font-display); }
  .att-reason { font-size: 13px; font-weight: 500; color: var(--c); }
  .att-hint { font-size: 13px; line-height: 1.4; color: var(--pp-text2); }

  /* Groups and cards */
  .group { display: grid; gap: 12px; scroll-margin-top: 76px; }
  .group-h { display: flex; align-items: baseline; gap: 10px; padding: 0 4px; }
  .group-h h3 { font: 600 20px / 1.2 var(--font-display); letter-spacing: -0.012em; }
  .gsub { font-size: 13px; color: var(--pp-text2); }
  .gcount { margin-left: auto; padding: 4px 10px; border-radius: 999px; background: var(--pp-surface2); font-size: 12px; font-weight: 500; color: var(--pp-text2); font-variant-numeric: tabular-nums; }
  .cards { display: grid; gap: 10px; }
  /* A card holds two controls side by side: the package itself (opens details) and its menu. */
  .pkg {
    position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 36px; align-items: center; column-gap: 14px;
    padding-right: 6px; border-radius: var(--r-md);
    background: var(--pp-card); border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-1);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .pkg-open {
    display: grid; grid-template-columns: 56px minmax(0, 1fr) auto; align-items: center; gap: 4px 14px; min-width: 0;
    padding: 14px 0 14px 16px; border: 0; border-radius: var(--r-md); background: none; text-align: left;
  }
  .pkg:hover { transform: translateY(-1px); box-shadow: var(--pp-shadow-2); }
  .pkg.menu-open { z-index: 4; }
  .ring { position: relative; display: block; width: 56px; height: 56px; flex: none; }
  .ring > svg { position: absolute; inset: 0; width: 100%; height: 100%; transform: rotate(-90deg); }
  .ring .seg { fill: none; stroke: var(--pp-ring-off); stroke-width: 3.5; stroke-linecap: round; }
  .ring .seg.on { stroke: var(--c); }
  .ring.pending .seg { stroke-dasharray: 3 5; }
  .ring .av { position: absolute; inset: 8px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--c) 14%, var(--pp-card)); color: var(--c); }
  .ring .av .ic { width: 22px; height: 22px; }
  .ring .done-badge {
    position: absolute; right: 1px; bottom: 1px; width: 18px; height: 18px; border-radius: 50%; display: grid; place-items: center;
    background: var(--st-delivered); color: var(--pp-card); box-shadow: 0 0 0 2px var(--pp-card);
  }
  .ring.lg { width: 96px; height: 96px; }
  .ring.lg .av { inset: 12px; }
  .ring.lg .av .ic { width: 36px; height: 36px; }
  .ring.lg .done-badge { width: 26px; height: 26px; right: 4px; bottom: 4px; }
  .ring.lg .done-badge .ic { width: 16px; height: 16px; }
  .pkg-main { min-width: 0; display: grid; gap: 2px; }
  .pkg-name { font: 500 17px / 1.25 var(--font-display); letter-spacing: -0.005em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pkg-status { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; color: var(--c); }
  .pkg-meta { font-size: 13px; color: var(--pp-text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .when { display: grid; justify-items: end; gap: 2px; text-align: right; }
  .when-main { font: 600 16px / 1.2 var(--font-display); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .when-sub { font-size: 12px; color: var(--pp-text2); white-space: nowrap; }
  .pkg.delivered .when-main { color: var(--pp-text2); font-weight: 500; }
  .kebab { width: 36px; height: 36px; color: var(--pp-text2); }
  .menu {
    position: absolute; z-index: 6; right: 8px; top: calc(100% - 6px); min-width: 220px; padding: 6px; border-radius: 14px;
    background: var(--pp-card); border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-2);
  }
  .menu button { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px 12px; border: 0; border-radius: 10px; background: none; font-size: 14px; text-align: left; color: var(--pp-text); }
  .menu button .ic { color: var(--pp-text2); }
  .menu button:hover { background: var(--pp-hover); }
  .menu .danger, .menu .danger .ic { color: var(--st-attention); }
  @media (max-width: 480px) {
    .pkg { grid-template-columns: minmax(0, 1fr) 32px; column-gap: 10px; padding-right: 2px; }
    .pkg-open { grid-template-columns: 48px minmax(0, 1fr) auto; gap: 2px 10px; padding: 12px 0 12px 12px; }
    .pkg .ring { width: 48px; height: 48px; }
    .pkg .ring .av { inset: 7px; }
    .pkg .ring .av .ic { width: 20px; height: 20px; }
    .pkg-name { font-size: 16px; }
    .when-main { font-size: 15px; }
    .kebab { width: 32px; height: 32px; }
  }
  .no-match { display: grid; justify-items: center; gap: 10px; padding: 40px 16px; text-align: center; color: var(--pp-text2); }

  /* Empty state */
  .empty { display: grid; justify-items: center; gap: 14px; padding: 56px 16px 24px; text-align: center; }
  .empty-art { position: relative; width: 168px; height: 168px; display: grid; place-items: center; }
  .empty-art .halo { position: absolute; inset: 0; border-radius: 50%; background: color-mix(in srgb, var(--pp-primary) 8%, transparent); }
  .empty-art .halo.two { inset: 22px; background: color-mix(in srgb, var(--pp-primary) 12%, var(--pp-card)); }
  .empty-art .box { position: relative; width: 76px; height: 76px; border-radius: 24px; display: grid; place-items: center; background: var(--pp-card); color: var(--pp-primary); box-shadow: var(--pp-shadow-2); }
  .empty-art .box .ic { width: 40px; height: 40px; }
  .empty h2 { font: 600 26px / 1.15 var(--font-display); letter-spacing: -0.015em; }
  .empty p { max-width: 44ch; color: var(--pp-text2); font-size: 15px; }

  /* Buttons */
  .fab {
    position: fixed; z-index: 7; right: 24px; bottom: 24px; display: inline-flex; align-items: center; gap: 10px; height: 56px; padding: 0 24px 0 18px;
    border: 0; border-radius: 18px; background: var(--pp-primary); color: var(--pp-on-primary);
    font: 500 16px / 1 var(--font-display); box-shadow: 0 8px 24px color-mix(in srgb, var(--pp-primary) 35%, transparent), var(--pp-shadow-1);
  }
  .fab:hover { filter: brightness(1.06); }
  .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; height: 40px; padding: 0 18px; border: 0; border-radius: 999px; font-size: 14px; font-weight: 500; white-space: nowrap; text-decoration: none; }
  .btn .ic { width: 18px; height: 18px; }
  .btn.sm { height: 32px; padding: 0 12px; font-size: 13px; }
  .btn.lg { height: 48px; padding: 0 24px; font-size: 15px; }
  .btn.text { background: none; color: var(--pp-primary); padding: 0 12px; }
  .btn.text:hover { background: color-mix(in srgb, var(--pp-primary) 10%, transparent); }
  .btn.filled { background: var(--pp-primary); color: var(--pp-on-primary); }
  .btn.filled:disabled { background: var(--pp-disabled-bg); color: var(--pp-text3); cursor: not-allowed; }
  .btn.tonal { background: var(--pp-surface2); color: var(--pp-text); }
  .btn.tonal:hover { background: color-mix(in srgb, var(--pp-text) 10%, var(--pp-surface2)); }
  .btn.danger { background: var(--pp-danger); color: var(--pp-on-danger); }
  .btn.danger:disabled, .btn.text:disabled { opacity: 0.6; cursor: progress; }
  .btn.danger-text { background: none; color: var(--st-attention); }
  .btn.danger-text:hover { background: color-mix(in srgb, var(--st-attention) 10%, transparent); }

  /* Details sheet */
  .scrim { position: fixed; inset: 0; z-index: 20; background: var(--pp-scrim); animation: fade 0.18s ease-out; }
  .scrim.top { z-index: 30; }
  @keyframes fade { from { opacity: 0; } }
  @keyframes slide-in { from { transform: translateX(36px); opacity: 0; } }
  @keyframes slide-up { from { transform: translateY(44px); opacity: 0; } }
  @keyframes pop { from { opacity: 0; transform: translate(-50%, -48%) scale(0.98); } }
  .sheet {
    position: fixed; z-index: 21; top: 0; right: 0; bottom: 0; width: min(480px, 100%); display: flex; flex-direction: column;
    background: var(--pp-card); box-shadow: -16px 0 48px rgba(0, 0, 0, 0.18); animation: slide-in 0.26s cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  .sheet-bar { display: flex; align-items: center; justify-content: flex-end; padding: 10px 10px 0; }
  .grab { display: none; }
  .sheet-body { flex: 1; overflow: auto; display: grid; align-content: start; gap: 22px; padding: 0 24px 28px; }
  .sheet-hero { display: grid; justify-items: center; gap: 12px; padding-top: 2px; text-align: center; }
  .sheet-hero h2 { font: 600 26px / 1.15 var(--font-display); letter-spacing: -0.015em; overflow-wrap: anywhere; }
  .pill { display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 13px 0 10px; border-radius: 999px; background: color-mix(in srgb, var(--c) 13%, transparent); color: var(--c); font-size: 13px; font-weight: 500; }
  .eta-card { display: grid; gap: 4px; padding: 16px 18px; border-radius: 16px; background: var(--pp-surface2); border: 1px solid var(--pp-card-line); }
  .eta-card .em { font: 600 21px / 1.2 var(--font-display); letter-spacing: -0.01em; }
  .eta-card .es { font-size: 14px; color: var(--pp-text2); }
  .eta-card .ec { margin-top: 2px; font-size: 13px; font-weight: 500; color: var(--c); }
  .journey { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .journey .j { position: relative; display: grid; justify-items: center; gap: 8px; padding: 0 2px; text-align: center; font-size: 12px; line-height: 1.25; color: var(--pp-text2); }
  .journey .j:not(:last-child)::after { content: ''; position: absolute; top: 18px; left: calc(50% + 24px); right: calc(-50% + 24px); height: 3px; border-radius: 3px; background: var(--pp-ring-off); }
  .journey .j.done:not(:last-child)::after { background: var(--c); }
  .journey .ji { width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; background: var(--pp-surface2); color: var(--pp-text3); border: 2px solid var(--pp-ring-off); }
  .journey .j.done .ji { background: var(--c); border-color: var(--c); color: var(--pp-card); }
  .journey .j.cur .ji { background: color-mix(in srgb, var(--c) 14%, var(--pp-card)); border-color: var(--c); color: var(--c); box-shadow: 0 0 0 5px color-mix(in srgb, var(--c) 15%, transparent); }
  .journey .j.done, .journey .j.cur { color: var(--pp-text); }
  .journey .j.cur { font-weight: 600; }
  .sec-h { margin-bottom: 12px; font: 600 16px / 1.2 var(--font-display); }
  .timeline { list-style: none; margin: 0; padding: 0; }
  .ev { position: relative; display: grid; grid-template-columns: 14px minmax(0, 1fr); gap: 14px; padding-bottom: 16px; }
  .ev:not(:last-child)::before { content: ''; position: absolute; left: 6px; top: 17px; bottom: 0; width: 2px; background: var(--pp-ring-off); }
  .ev .b { width: 14px; height: 14px; margin-top: 3px; border-radius: 50%; border: 2px solid var(--pp-ring-off); background: var(--pp-card); }
  .ev:first-child .b { border-color: var(--c); background: var(--c); box-shadow: 0 0 0 4px color-mix(in srgb, var(--c) 18%, transparent); }
  .ev .e { line-height: 1.35; }
  .ev:first-child .e { font-weight: 500; }
  .ev .m { margin-top: 2px; font-size: 12px; color: var(--pp-text2); }
  .ev .a { margin-top: 4px; font-size: 13px; line-height: 1.4; color: var(--pp-text2); }
  .facts { border-radius: 14px; background: var(--pp-surface2); border: 1px solid var(--pp-card-line); }
  .fact { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 6px 8px 6px 14px; }
  .fact + .fact { border-top: 1px solid var(--pp-line); }
  .fk { font-size: 13px; color: var(--pp-text2); white-space: nowrap; }
  .fv { display: inline-flex; align-items: center; gap: 2px; min-width: 0; font-weight: 500; text-align: right; overflow-wrap: anywhere; }
  .fv.mono { font: 400 13px / 1.3 var(--font-mono); letter-spacing: 0.02em; }
  .icon-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .ic-choice { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; border: 1px solid var(--pp-card-line); background: var(--pp-card); color: var(--pp-text2); }
  .ic-choice:hover { color: var(--pp-text); border-color: var(--pp-input-line); }
  .ic-choice[aria-pressed='true'] { border-color: var(--pp-primary); background: var(--pp-selected); color: var(--pp-primary); }
  .sheet-foot { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 12px 16px; border-top: 1px solid var(--pp-line); }
  @media (max-width: 600px) {
    .sheet { top: auto; left: 0; width: 100%; max-height: 92%; border-radius: 22px 22px 0 0; box-shadow: 0 -16px 48px rgba(0, 0, 0, 0.22); animation-name: slide-up; }
    .sheet-bar { justify-content: space-between; padding: 8px 8px 0 16px; }
    .grab { display: block; width: 40px; height: 4px; margin-left: calc(50% - 36px); border-radius: 2px; background: var(--pp-ring-off); }
    .sheet-body { padding: 0 18px 24px; }
  }

  /* Dialogs */
  .dialog {
    position: fixed; z-index: 31; left: 50%; top: 50%; transform: translate(-50%, -50%);
    width: min(540px, calc(100% - 32px)); max-height: calc(100% - 48px); overflow: auto; display: flex; flex-direction: column;
    background: var(--pp-card); border-radius: 24px; box-shadow: 0 28px 72px rgba(0, 0, 0, 0.24); animation: pop 0.2s ease-out;
  }
  .dialog > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 22px 14px 4px 26px; }
  .dialog h2 { font: 600 24px / 1.2 var(--font-display); letter-spacing: -0.015em; }
  .dsub { margin-top: 4px; font-size: 14px; color: var(--pp-text2); }
  .form { display: grid; gap: 20px; padding: 16px 26px 8px; }
  .field { position: relative; display: grid; gap: 8px; }
  .field > label { font-size: 13px; font-weight: 500; color: var(--pp-text2); }
  .input { width: 100%; height: 50px; padding: 0 14px; border: 1px solid var(--pp-input-line); border-radius: 14px; background: var(--pp-input-bg); color: var(--pp-text); font-size: 15px; }
  select.input { appearance: auto; }
  .input.xl { height: 58px; font-size: 18px; }
  .input::placeholder { color: var(--pp-text3); }
  .input:focus { outline: none; border-color: var(--pp-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--pp-primary) 20%, transparent); }
  .input.mono { font-family: var(--font-mono); letter-spacing: 0.04em; }
  .help { font-size: 13px; line-height: 1.4; color: var(--pp-text2); }
  .form-error { display: flex; align-items: flex-start; gap: 8px; padding: 10px 14px; border-radius: 12px; font-size: 14px; background: color-mix(in srgb, var(--st-attention) 9%, var(--pp-card)); color: var(--st-attention); }
  .carrier-row { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 10px 6px 10px 14px; border-radius: 14px; background: color-mix(in srgb, var(--st-delivered) 9%, var(--pp-card)); color: var(--st-delivered); }
  .carrier-row.warn { background: color-mix(in srgb, var(--st-failed) 9%, var(--pp-card)); color: var(--st-failed); }
  .cr-text { display: grid; gap: 2px; font-size: 14px; color: var(--pp-text); }
  .cr-text b { font-weight: 600; }
  .cr-warn { font-size: 13px; color: var(--st-failed); }
  .combo-wrap { position: relative; }
  .combo-wrap .caret { position: absolute; right: 14px; top: 15px; color: var(--pp-text2); pointer-events: none; }
  .combo-list { position: absolute; z-index: 3; left: 0; right: 0; top: calc(100% + 6px); max-height: 260px; overflow: auto; padding: 6px; background: var(--pp-card); border: 1px solid var(--pp-card-line); border-radius: 14px; box-shadow: var(--pp-shadow-2); }
  .opt-head { padding: 8px 10px 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--pp-text2); }
  .opt { display: flex; justify-content: space-between; gap: 12px; padding: 10px; border-radius: 10px; cursor: pointer; }
  .opt:hover, .opt[aria-selected='true'] { background: var(--pp-surface2); }
  .opt .code { font: 12px / 1.6 var(--font-mono); color: var(--pp-text2); }
  .opt-empty { padding: 10px; font-size: 13px; color: var(--pp-text2); }
  .desc-row { display: grid; grid-template-columns: 50px minmax(0, 1fr); gap: 10px; align-items: center; }
  .desc-av { width: 50px; height: 50px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--pp-primary) 12%, var(--pp-card)); color: var(--pp-primary); }
  .toggle-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 2px 0; cursor: pointer; }
  .toggle-row > span { display: grid; gap: 2px; }
  .toggle-title { font-size: 14px; font-weight: 500; }
  .switch { appearance: none; -webkit-appearance: none; position: relative; flex: none; width: 46px; height: 28px; margin: 0; border-radius: 999px; background: var(--pp-switch-off); cursor: pointer; transition: background 0.15s; }
  .switch::after { content: ''; position: absolute; top: 3px; left: 3px; width: 22px; height: 22px; border-radius: 50%; background: #ffffff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25); transition: transform 0.15s; }
  .switch:checked { background: var(--pp-primary); }
  .switch:checked::after { transform: translateX(18px); }
  .dialog > footer { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 16px 18px 20px 26px; }
  .quota { margin-right: auto; font-size: 12px; color: var(--pp-text2); }
  .dialog.small { width: min(420px, calc(100% - 32px)); padding: 26px 24px 18px; gap: 10px; align-items: center; text-align: center; }
  .dialog.small p { max-width: 36ch; font-size: 14px; color: var(--pp-text2); }
  .dialog.small .actions { display: flex; justify-content: center; gap: 8px; margin-top: 10px; }
  .cf-ic { width: 52px; height: 52px; margin-bottom: 4px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--st-attention) 13%, transparent); color: var(--st-attention); }
  .cf-ic.info { background: color-mix(in srgb, var(--pp-primary) 13%, transparent); color: var(--pp-primary); }
  @media (max-width: 600px) {
    .dialog { left: 0; right: 0; top: auto; bottom: 0; transform: none; width: 100%; max-height: 94%; border-radius: 24px 24px 0 0; animation-name: slide-up; }
    .dialog.small { width: 100%; }
    .form { padding: 14px 18px 8px; }
    .dialog > header { padding: 20px 10px 4px 18px; }
    .dialog > footer { padding: 14px 14px 18px 18px; }
  }

  /* Toast */
  .toast {
    position: fixed; z-index: 40; left: 50%; bottom: 100px; transform: translateX(-50%); display: flex; align-items: center; gap: 10px;
    width: max-content; max-width: calc(100% - 32px); padding: 12px 18px 12px 14px; border-radius: 14px;
    background: var(--pp-toast-bg); color: var(--pp-toast-fg); font-size: 14px; box-shadow: var(--pp-shadow-2); animation: toast-in 0.2s ease-out;
  }
  .toast.error .ic { color: var(--st-attention); }
  @keyframes toast-in { from { opacity: 0; transform: translate(-50%, 8px); } }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
`;var D5="https://github.com/kedube/ha-parcel#let-home-assistant-delete-packages",Z=(L,C="")=>A`<svg class="ic ${C}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d=${L}></path></svg>`,b=(L,C="")=>Z(G2(L),C);function E5(L){if(document.getElementById("parcel-panel-fonts"))return;let C=document.createElement("style");C.id="parcel-panel-fonts",C.textContent=[400,500,600].map(H=>`@font-face{font-family:"Parcel Outfit";font-style:normal;font-weight:${H};font-display:swap;src:url("${L}/fonts/outfit-latin-${H}-normal.woff2") format("woff2");}`).join(""),document.head.appendChild(C)}var K=class extends k{constructor(){super(),this._payload=null,this._subError="",this._query="",this._searchOpen=!1,this._selectedUid=null,this._showAllEvents=!1,this._iconsOpen=!1,this._menuFor=null,this._confirmFor=null,this._deleting=!1,this._addOpen=!1,this._form=this._blankForm(),this._carriers=null,this._toast=null,this._refreshing=!1,this._tick=0,this._roadWidth=0,this._items=[],this._iconRules=[],this._onKey=this._onKey.bind(this),this._onReconnect=this._onReconnect.bind(this),this._onDocClick=()=>{this._menuFor&&(this._menuFor=null)}}connectedCallback(){super.connectedCallback(),E5(this.panel?.config?.static_url||"/parcel_static"),window.addEventListener("keydown",this._onKey),window.addEventListener("click",this._onDocClick),this._timer=setInterval(()=>{this._tick+=1,this._subscribe()},3e4),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),window.removeEventListener("click",this._onDocClick),clearInterval(this._timer),clearTimeout(this._toastTimer),this._roadObserver?.disconnect(),this._observedRoad=null,this._unsubscribe()}shouldUpdate(C){if(C.size===1&&C.has("hass")){let H=C.get("hass");return!H||!this.hass?!0:H.themes?.darkMode!==this.hass.themes?.darkMode||H.locale!==this.hass.locale||H.language!==this.hass.language||H.dockedSidebar!==this.hass.dockedSidebar}return!0}willUpdate(C){if((!this._fmt||C.has("hass"))&&(this._fmt=Z1(this.hass)),C.has("panel")&&(this._iconRules=c1(this.panel?.config?.icon_rules)),C.has("_payload")){this._items=X2(this._payload);let H=new Set(this._items.map(V=>V.uid));this._selectedUid&&!H.has(this._selectedUid)&&(this._selectedUid=null),this._menuFor&&!H.has(this._menuFor)&&(this._menuFor=null)}}updated(C){C.has("hass")&&(this.toggleAttribute("dark",!!this.hass?.themes?.darkMode),this._subscribe());let H=this.renderRoot.querySelector(".hours");H!==this._observedRoad&&(this._roadObserver??=new ResizeObserver(([V])=>{let M=Math.round(V.contentRect.width);M&&M!==this._roadWidth&&(this._roadWidth=M)}),this._observedRoad&&this._roadObserver.unobserve(this._observedRoad),H&&this._roadObserver.observe(H),this._observedRoad=H)}_subscribe(){if(this._unsub||!this.hass||!this.isConnected)return;let C=this.hass.connection;this._connection!==C&&(this._connection?.removeEventListener("ready",this._onReconnect),C.addEventListener("ready",this._onReconnect),this._connection=C),this._unsub=C.subscribeMessage(H=>{this._subError="",this._payload=H},{type:"parcel/subscribe"},{resubscribe:!1}).catch(H=>{this._subError=H?.message||"Couldn\u2019t load packages",this._unsub=void 0})}_onReconnect(){this._unsub=void 0,this._subscribe()}_unsubscribe(){this._connection?.removeEventListener("ready",this._onReconnect),this._connection=void 0,this._unsub&&(this._unsub.then(C=>C?.()).catch(()=>{}),this._unsub=void 0)}get _entries(){return this._payload?.entries||[]}get _iconChoices(){return this.panel?.config?.icon_choices||[]}_modal(){return this._confirmFor?this.renderRoot.querySelector(".dialog.small"):this._addOpen?this.renderRoot.querySelector("form.dialog"):this._selectedUid?this.renderRoot.querySelector(".sheet"):null}_onKey(C){if(C.key==="Tab"){let H=this._modal();if(!H)return;let V=[...H.querySelectorAll(o5)].filter(r=>r.getClientRects().length>0),M=a5(V,this.renderRoot.activeElement,C.shiftKey);(M||!V.length)&&(C.preventDefault(),M?.focus());return}C.key==="Escape"&&(this._confirmFor?this._closeConfirm():this._addOpen&&this._form.carrierOpen?this._setForm({carrierOpen:!1}):this._addOpen?this._closeAdd():this._selectedUid?this._closeDetails():this._menuFor?this._menuFor=null:this._searchOpen&&(this._query="",this._searchOpen=!1))}_restoreFocus(C){this.updateComplete.then(()=>C?.focus?.())}_toggleSidebar(){this.dispatchEvent(new Event("hass-toggle-menu",{bubbles:!0,composed:!0}))}_showToast(C,H=!1){this._toast={message:C,error:H},clearTimeout(this._toastTimer),this._toastTimer=setTimeout(()=>{this._toast=null},H?6e3:4e3)}async _copy(C){let H=this.renderRoot.activeElement,V=await U1(C);H?.focus?.(),this._showToast(V?"Tracking number copied":`Couldn\u2019t copy automatically. The number is ${C}`)}async _refresh(){if(!this._refreshing){this._refreshing=!0;try{await this.hass.callWS({type:"parcel/refresh"}),this._showToast("Up to date with Parcel")}catch(C){this._showToast(C?.message||"Couldn\u2019t check Parcel",!0)}finally{this._refreshing=!1}}}_openSearch(){this._searchOpen=!0,this.updateComplete.then(()=>this.renderRoot.querySelector("#q")?.focus())}_openDetails(C,H={}){this._lastFocus=this.renderRoot.activeElement||document.activeElement,this._menuFor=null,this._selectedUid=C.uid,this._showAllEvents=!1,this._iconsOpen=!!H.icons,this.updateComplete.then(()=>this.renderRoot.querySelector(".sheet .icon-btn")?.focus())}_closeDetails(){this._selectedUid=null,this._restoreFocus(this._lastFocus)}_askDelete(C){this._confirmFocus=this.renderRoot.activeElement||document.activeElement,this._menuFor=null,this._confirmFor=C,this.updateComplete.then(()=>this.renderRoot.querySelector(".dialog.small .btn")?.focus())}_closeConfirm(){this._deleting||(this._confirmFor=null,this._restoreFocus(this._confirmFocus))}async _doDelete(C){this._deleting=!0;try{await this.hass.callWS({type:"parcel/delete",entry_id:C.entryId,key:C.key}),this._selectedUid===C.uid&&(this._selectedUid=null),this._showToast(`Deleted \u201C${C.description}\u201D`)}catch(H){this._showToast(H?.message||"Couldn\u2019t delete the package",!0)}finally{this._deleting=!1,this._confirmFor=null}}async _setIcon(C,H){try{await this.hass.callWS({type:"parcel/set_icon",entry_id:C.entryId,key:C.key,icon:H})}catch(V){this._showToast(V?.message||"Couldn\u2019t change the icon",!0)}}_scrollTo(C){let H=window.matchMedia("(prefers-reduced-motion: reduce)").matches;this.renderRoot.querySelector(`#${C}`)?.scrollIntoView({behavior:H?"auto":"smooth",block:"start"})}_blankForm(){return{entryId:"",number:"",carrier:"",carrierEditing:!1,carrierQuery:"",carrierOpen:!1,active:0,description:"",icon:"",extra:"",push:!0,submitting:!1,error:""}}_setForm(C){this._form={...this._form,...C}}async _loadCarriers(){try{let C=await this.hass.callWS({type:"parcel/carriers"});this._carriers={list:C.carriers||{},suggested:C.suggested||[],detect:c1(C.detect,"")}}catch(C){this._carriers={list:{},suggested:[],detect:[],error:C?.message||"Couldn\u2019t load carriers"}}}_openAdd(){this._lastFocus=this.renderRoot.activeElement||document.activeElement,this._menuFor=null,this._form={...this._blankForm(),entryId:this._entries[0]?.entry_id||""},this._addOpen=!0,(!this._carriers||this._carriers.error)&&this._loadCarriers(),this.updateComplete.then(()=>this.renderRoot.querySelector("#f-number")?.focus())}_closeAdd(){this._addOpen=!1,this._restoreFocus(this._lastFocus)}_carrierName(C){return this._carriers?.list?.[C]?.name||C.toUpperCase()}_pickCarrier(C){this._setForm({carrier:C,carrierEditing:!1,carrierOpen:!1,carrierQuery:"",extra:""}),this.updateComplete.then(()=>this.renderRoot.querySelector("#f-desc")?.focus())}_onComboKey(C,H){let V=H.items.length;if(!V)return;let M=()=>this.updateComplete.then(()=>this.renderRoot.querySelector('.opt[aria-selected="true"]')?.scrollIntoView({block:"nearest"}));C.key==="ArrowDown"?(C.preventDefault(),this._setForm({active:(this._form.active+1)%V,carrierOpen:!0}),M()):C.key==="ArrowUp"?(C.preventDefault(),this._setForm({active:(this._form.active-1+V)%V}),M()):C.key==="Enter"&&this._form.carrierOpen&&(C.preventDefault(),this._pickCarrier(H.items[Math.min(this._form.active,V-1)].code))}async _submitAdd(C,H){if(C.preventDefault(),!H.valid||this._form.submitting)return;let V=this._form.description.trim();this._setForm({submitting:!0,error:""});try{await this.hass.callWS({type:"parcel/add",entry_id:H.entryId||void 0,tracking_number:H.number,description:V,carrier_code:H.carrier,extra:this._form.extra.trim()||null,send_push_confirmation:this._form.push,icon:this._form.icon||null}),this._addOpen=!1,this._query="",this._showToast(`Now tracking \u201C${V}\u201D. The first update usually takes a few minutes.`),this.updateComplete.then(()=>this._scrollTo("sec-new"))}catch(M){this._setForm({submitting:!1,error:M?.message||"Couldn\u2019t add the package"})}}render(){this._fmt||(this._fmt=Z1(this.hass));let C=new Date,H=this._fmt.ymd(C),V={fmt:this._fmt,today:H,now:C,roadWidth:this._roadWidth},M=this.narrow||this.hass?.dockedSidebar==="always_hidden",r=this._entries,e=r.map(x=>S(x.updated_at)).filter(Boolean).sort((x,s)=>s-x)[0],i=this._query.trim().length>0,t=Y2(this._items,H,this._fmt),p=this._selectedUid?this._items.find(x=>x.uid===this._selectedUid):null,n=!!(p||this._addOpen||this._confirmFor),d;this._subError&&!this._payload?d=A`<div class="banner">${Z(v.warn)}<span>${this._subError}</span></div>`:this._payload?r.length?this._items.length?i?d=this._renderResults(V):d=A`${this._renderHero(t,V)}${this._renderAttention(t.attention,V)}${V1.map(x=>this._renderGroup(x,t[x],V))}`:d=this._renderEmpty():d=A`<p class="loading">Parcel isn’t set up. Add it in Settings › Devices &amp; services.</p>`:d=A`<p class="loading">Loading packages…</p>`;let a=r.filter(x=>x.last_error),m=r.filter(x=>{let s=S(x.paused_until);return s&&s>C});return A`
      <header class="appbar ${this._searchOpen?"searching":""}" ?inert=${n}>
        <div class="appbar-inner">
          ${M?A`<button class="icon-btn" aria-label="Show sidebar" @click=${this._toggleSidebar}>${Z(v.menu)}</button>`:l}
          <h1>Packages</h1>
          <div class="spacer"></div>
          ${this._searchOpen?A`<label class="search">${Z(v.search,"sm")}
                <input id="q" type="search" placeholder="Search by name, number or carrier" aria-label="Search packages"
                  .value=${this._query} @input=${x=>{this._query=x.target.value}}>
                <button class="icon-btn tiny" aria-label="Close search" @click=${()=>{this._query="",this._searchOpen=!1}}>${Z(v.close,"xs")}</button>
              </label>`:A`<button class="icon-btn" aria-label="Search packages" title="Search packages" @click=${this._openSearch}>${Z(v.search)}</button>`}
          ${e?A`<span class="updated" title="Home Assistant checks Parcel every few minutes. Parcel allows 20 checks an hour.">
            ${this._refreshing?"Checking\u2026":`Updated ${L1(e,C)}`}</span>`:l}
          <button class="icon-btn ${this._refreshing?"spin":""}" aria-label="Check Parcel for updates" title="Check Parcel for updates" @click=${this._refresh}>${Z(v.refresh)}</button>
        </div>
      </header>
      <main class="main" ?inert=${n}>
        ${this._subError&&this._payload?A`<div class="banner" role="status">${Z(v.warn)}<span>Lost touch with Home Assistant, so this may be out of date. Trying again…</span></div>`:l}
        ${a.map(x=>A`<div class="banner" role="status">${Z(v.warn)}<span>${r.length>1?`${x.title}: `:""}${x.last_error}</span></div>`)}
        ${m.map(x=>A`<div class="banner info" role="status">${Z(v.info)}<span>${r.length>1?`${x.title}: `:""}Parcel asked Home Assistant to slow down. This is the last update it has; it will check again around ${this._fmt.time(S(x.paused_until))}.</span></div>`)}
        ${d}
      </main>
      ${r.length?A`<button class="fab" ?inert=${n} @click=${this._openAdd}>${Z(v.plus)}<span>Add package</span></button>`:l}
      ${p?this._renderSheet(p,V):l}
      ${this._addOpen?this._renderAdd():l}
      ${this._confirmFor?this._renderConfirm():l}
      ${this._toast?A`<div class="toast ${this._toast.error?"error":""}" role="status" aria-live="polite">
            ${Z(this._toast.error?v.warn:v.checkCircle,"sm")}<span>${this._toast.message}</span></div>`:l}
    `}_greeting(C){let H=this._fmt.hours(C);return H<12?"Good morning":H<17?"Good afternoon":"Good evening"}_renderHero(C,H){let{fmt:V,today:M,now:r}=H,e=r5(C,H),i;if(e.kind==="today"){let t=e.count===1;i=A`<span class="n">${e.count} ${t?"package":"packages"}</span> ${t?"arrives":"arrive"} today`}else e.kind==="delivered"?i=A`<span class="n">Today’s deliveries</span> are in`:i=A`Nothing arriving today`;return A`<section class="hero" aria-labelledby="hero-h" style="--c: var(${e.color})">
      <div class="hero-top">
        <div>
          <div class="greet">${this._greeting(r)}</div>
          <h2 class="hero-h" id="hero-h">${i}</h2>
          <p class="hero-sub">${e.sub}</p>
        </div>
        <div class="cal" aria-hidden="true">
          <span class="dow">${V.weekday(M,"short")}</span>
          <span class="dom">${V.dayNumber(M)}</span>
          <span class="mon">${V.monthShort(M)}</span>
        </div>
      </div>
      ${this._renderRoad(e.todays,e.deliveredToday,H)}
      ${e.stats.length?A`<div class="hero-stats">${e.stats.map(t=>A`
            <button class="stat" style="--c: var(${t.color})" @click=${()=>this._scrollTo(t.target)}><span class="sn">${t.n}</span>${t.label}</button>`)}</div>`:l}
    </section>`}_renderRoad(C,H,V){let M=e5(C,H,V);if(!M)return l;let{pins:r,anytime:e}=M;return A`<div class="road-wrap" style="--lanes: ${M.lanes}">
      ${r.length?A`
          <div class="pins">
            ${r.map(i=>A`<button class="pin ${i.x<14?"edge-l":i.x>86?"edge-r":""} ${i.done?"done":""}"
                style="left: ${i.x}%; --lane: ${i.lane}; --c: var(${i.st.color})" aria-label="${i.d.description}, ${i.label}"
                @click=${()=>this._openDetails(i.d)}>
              <span class="tip">${i.d.description} · ${i.label}</span>
              <span class="pin-av">${b(i.d.icon)}${i.done?A`<span class="pin-check">${Z(v.check,"xxs")}</span>`:l}</span>
              <span class="stem"></span>
            </button>`)}
          </div>
          <div class="road" aria-hidden="true">
            ${M.bands.map(i=>A`<span class="band" style="left: ${i.left}%; width: ${i.width}%; --c: var(${i.color})"></span>`)}
            <span class="now-truck" style="left: ${M.nowLeft}%" title="Now, ${V.fmt.time(V.now)}">${Z(v.truckNow,"xs")}</span>
          </div>
          <div class="hours" aria-hidden="true">
            ${M.ticks.map(i=>i.hidden?l:A`<span class="tick" style="left: ${i.left}%">${i.label}</span>`)}
            <span class="now-lab" style="left: ${M.nowLeft}%">Now</span>
          </div>`:l}
      ${e.length?A`<div class="anytime"><span class="any-label">Any time today:</span>
            ${e.map(i=>A`<button class="any-chip" style="--c: var(${O(i).color})" @click=${()=>this._openDetails(i)}>
              <span class="any-av">${b(i.icon,"xs")}</span><span class="any-name">${i.description}</span></button>`)}</div>`:l}
    </div>`}_renderAttention(C,H){return C.length?A`<section class="attention" id="sec-attention" aria-labelledby="att-h">
      <div class="att-head">
        <span class="att-ic">${Z(v.alert)}</span>
        <div><h3 id="att-h">${C.length===1?"1 package needs a look":`${C.length} packages need a look`}</h3>
          <p>Something changed that you may want to act on.</p></div>
      </div>
      ${C.map(V=>{let M=O(V),r=h1(V,M,H);return A`<button class="att-row" style="--c: var(${M.color})" @click=${()=>this._openDetails(V)}>
          <span class="att-av">${b(V.icon)}</span>
          <span class="att-text"><span class="att-name">${V.description}</span><span class="att-reason">${r.title}</span>${r.hint?A`<span class="att-hint">${r.hint}</span>`:l}</span>
          ${Z(v.chevronRight,"sm chev")}
        </button>`})}
    </section>`:l}_renderGroup(C,H,V){if(!H.length)return l;let M=q2[C];return A`<section class="group" id="sec-${C}" aria-labelledby="h-${C}">
      <div class="group-h"><h3 id="h-${C}">${M.title}</h3>${M.sub?A`<span class="gsub">${M.sub(V)}</span>`:l}<span class="gcount">${H.length}</span></div>
      <div class="cards">${H.map(r=>this._renderCard(r,V))}</div>
    </section>`}_renderResults(C){let H=this._items.filter(V=>J2(V,this._query));return H.length?A`<section class="group" aria-labelledby="h-results">
      <div class="group-h"><h3 id="h-results">Results</h3><span class="gcount">${H.length}</span></div>
      <div class="cards">${H.map(V=>this._renderCard(V,C))}</div>
    </section>`:A`<div class="no-match">${Z(v.search)}<p>No packages match “${this._query}”.</p>
        <button class="btn text" @click=${()=>{this._query=""}}>Clear search</button></div>`}_renderRing(C,H,V=""){let M=H.key==="pending"||H.key==="notfound"?0:H.stage+1,r=25,e=2*Math.PI*r,i=9,t=e/4-i;return A`<span class="ring ${V} ${H.key==="pending"?"pending":""}">
      <svg viewBox="0 0 56 56" aria-hidden="true">${[0,1,2,3].map(p=>N1`<circle class="seg ${p<M?"on":""}" cx="28" cy="28" r="${r}" stroke-dasharray="${t} ${e-t}" stroke-dashoffset="${-(p*e)/4-i/2}"></circle>`)}</svg>
      <span class="av">${b(C.icon)}</span>
      ${H.key==="delivered"?A`<span class="done-badge">${Z(v.check,"xxs")}</span>`:l}
    </span>`}_renderCard(C,H){let V=O(C),M=V5(C,V,H),r=this._menuFor===C.uid;return A`<article class="pkg ${V.key} ${r?"menu-open":""}" style="--c: var(${V.color})">
      <button class="pkg-open" aria-label="${C.description}: ${V.label}. ${M.main} ${M.sub}. Show details" @click=${()=>this._openDetails(C)}>
        ${this._renderRing(C,V)}
        <span class="pkg-main">
          <span class="pkg-name">${C.description}</span>
          <span class="pkg-status">${Z(v[V.icon],"xs")}${V.label}</span>
          <span class="pkg-meta">${L5(C,H)}</span>
        </span>
        <span class="when"><span class="when-main">${M.main}</span>${M.sub?A`<span class="when-sub">${M.sub}</span>`:l}</span>
      </button>
      <button class="icon-btn kebab" aria-label="More for ${C.description}" aria-haspopup="menu" aria-expanded=${String(r)}
        @click=${e=>{e.stopPropagation(),this._menuFor=r?null:C.uid}}>${Z(v.more,"sm")}</button>
      ${r?A`<div class="menu" role="menu" @click=${e=>e.stopPropagation()}>
            <button role="menuitem" @click=${()=>{this._menuFor=null,this._copy(C.trackingNumber)}}>${Z(v.copy,"sm")}Copy tracking number</button>
            <button role="menuitem" @click=${()=>this._openDetails(C,{icons:!0})}>${Z(v.shape,"sm")}Change icon</button>
            <button role="menuitem" class="danger" @click=${()=>this._askDelete(C)}>${Z(v.delete,"sm")}Delete…</button>
          </div>`:l}
    </article>`}_renderSheet(C,H){let V=O(C),M=M5(C,V,H),r=V.key==="pickup"?K2:H1,e=V.stage,i=this._showAllEvents?C.events:C.events.slice(0,3),t=this._entries.length>1;return A`
      <div class="scrim" @click=${this._closeDetails}></div>
      <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" style="--c: var(${V.color})" ?inert=${!!this._confirmFor}>
        <div class="sheet-bar"><span class="grab" aria-hidden="true"></span>
          <button class="icon-btn" aria-label="Close" @click=${this._closeDetails}>${Z(v.close)}</button></div>
        <div class="sheet-body">
          <div class="sheet-hero">
            ${this._renderRing(C,V,"lg")}
            <h2 id="sheet-title">${C.description}</h2>
            <span class="pill">${Z(v[V.icon],"xs")}${V.label}</span>
          </div>
          <div class="eta-card">
            <span class="em">${M.main}</span>
            ${M.sub?A`<span class="es">${M.sub}</span>`:l}
            ${M.note?A`<span class="ec">${M.note}</span>`:l}
          </div>
          <ol class="journey" aria-label="Delivery progress">${r.map((p,n)=>A`<li class="j ${n<e||V.key==="delivered"?"done":""} ${n===e&&V.key!=="delivered"?"cur":""}">
              <span class="ji">${Z(v[p.icon],"sm")}</span><span>${p.label}</span></li>`)}</ol>
          <section>
            <h3 class="sec-h">Updates</h3>
            ${C.events.length?A`<ol class="timeline">${i.map(p=>{let n=[p.location,p.when?H5(H.fmt,p.when,H.today):p.whenText].filter(Boolean).join(" \xB7 ");return A`<li class="ev"><span class="b"></span><div>
                    <div class="e">${p.text}</div>
                    ${n?A`<div class="m">${n}</div>`:l}
                    ${p.additional?A`<div class="a">${p.additional}</div>`:l}</div></li>`})}</ol>
                ${C.events.length>3?A`<button class="btn text sm" @click=${()=>{this._showAllEvents=!this._showAllEvents}}>${this._showAllEvents?"Show fewer":`Show all ${C.events.length} updates`}</button>`:l}`:A`<p class="muted">No updates yet. The first one usually shows up within a few hours of the carrier scanning the package.</p>`}
          </section>
          <section>
            <h3 class="sec-h">Details</h3>
            <div class="facts">
              <div class="fact"><span class="fk">Carrier</span><span class="fv">${C.carrierName}</span></div>
              <div class="fact"><span class="fk">Tracking number</span><span class="fv mono">${C.trackingNumber}
                <button class="icon-btn tiny" aria-label="Copy tracking number" title="Copy tracking number" @click=${()=>this._copy(C.trackingNumber)}>${Z(v.copy,"xs")}</button></span></div>
              ${t?A`<div class="fact"><span class="fk">Parcel account</span><span class="fv">${C.entryTitle}</span></div>`:l}
              <div class="fact"><span class="fk">Icon · ${C.iconSource==="user"?"your choice":"matched to the name"}</span><span class="fv">
                <button class="btn text sm" @click=${()=>{this._iconsOpen=!this._iconsOpen}}>${b(C.icon,"sm")}${this._iconsOpen?"Done":"Change"}</button></span></div>
            </div>
            ${this._iconsOpen?A`<div class="icon-row" role="group" aria-label="Choose an icon" style="margin-top: 12px">
                  ${this._iconChoices.map(p=>A`<button class="ic-choice" aria-pressed=${String(p===C.icon)} aria-label=${Q[p]||p} title=${Q[p]||p}
                    @click=${()=>this._setIcon(C,p)}>${b(p,"sm")}</button>`)}
                  ${C.iconSource==="user"?A`<button class="btn text sm" @click=${()=>this._setIcon(C,null)}>Match the name again</button>`:l}
                </div>`:l}
          </section>
        </div>
        <div class="sheet-foot">
          <button class="btn tonal" @click=${()=>this._copy(C.trackingNumber)}>${Z(v.copy,"sm")}Copy number</button>
          <button class="btn danger-text" @click=${()=>this._askDelete(C)}>${Z(v.delete,"sm")}Delete</button>
        </div>
      </aside>`}_renderConfirm(){let C=this._confirmFor;return C.canDelete?A`<div class="scrim top" @click=${this._closeConfirm}></div>
      <div class="dialog small" role="alertdialog" aria-modal="true" aria-labelledby="cf-title">
        <span class="cf-ic">${Z(v.delete)}</span>
        <h2 id="cf-title">Delete “${C.description}”?</h2>
        <p>It will be removed from Parcel on all your devices. This can’t be undone.</p>
        <div class="actions">
          <button class="btn text" ?disabled=${this._deleting} @click=${this._closeConfirm}>Cancel</button>
          <button class="btn danger" ?disabled=${this._deleting} @click=${()=>this._doDelete(C)}>${this._deleting?"Deleting\u2026":"Delete"}</button>
        </div>
      </div>`:A`<div class="scrim top" @click=${this._closeConfirm}></div>
        <div class="dialog small" role="alertdialog" aria-modal="true" aria-labelledby="cf-title">
          <span class="cf-ic info">${Z(v.info)}</span>
          <h2 id="cf-title">Connect your Parcel sign-in</h2>
          <p>Parcel’s API can’t delete packages, so Home Assistant uses your Parcel web sign-in for this. Add it once under Settings › Devices &amp; services › Parcel › Configure.
            <a href=${D5} target="_blank" rel="noreferrer">How to find it</a></p>
          <div class="actions"><button class="btn filled" @click=${this._closeConfirm}>Got it</button></div>
        </div>`}_renderEmpty(){return A`<section class="empty">
      <div class="empty-art" aria-hidden="true"><span class="halo"></span><span class="halo two"></span><span class="box">${Z(v.empty)}</span></div>
      <h2>No packages on the way</h2>
      <p>Paste a tracking number to start following a delivery. Packages you add in the Parcel app show up here too.</p>
      <button class="btn filled lg" @click=${this._openAdd}>${Z(v.plus,"sm")}Add a package</button>
    </section>`}_renderCarrierCombo(C,H,V){let M=i5(this._carriers,C.carrierQuery,H),r=Object.keys(this._carriers?.list||{}).length;return A`<div class="field">
      <label for="f-carrier">Carrier</label>
      <div class="combo-wrap">
        <input id="f-carrier" class="input" role="combobox" aria-expanded=${String(C.carrierOpen)} aria-controls="carrier-list" aria-autocomplete="list" autocomplete="off"
          placeholder=${r?`Search ${r} carriers`:"Loading carriers\u2026"}
          .value=${C.carrierOpen?C.carrierQuery:V?.name??""}
          @focus=${()=>this._setForm({carrierOpen:!0,carrierQuery:"",active:0})}
          @blur=${()=>this._setForm({carrierOpen:!1})}
          @input=${e=>this._setForm({carrierQuery:e.target.value,carrierOpen:!0,active:0})}
          @keydown=${e=>this._onComboKey(e,M)}>
        ${Z(v.chevronDown,"sm caret")}
      </div>
      ${C.carrierOpen?A`<div class="combo-list" id="carrier-list" role="listbox" @mousedown=${e=>e.preventDefault()}>
            ${M.items.length?M.items.map((e,i)=>A`${e.heading?A`<div class="opt-head">${e.heading}</div>`:l}
                    <div class="opt" role="option" aria-selected=${String(i===C.active)} @click=${()=>this._pickCarrier(e.code)}><span>${e.name}</span><span class="code">${e.code}</span></div>`):A`<div class="opt-empty">${r?`No carrier matches \u201C${C.carrierQuery}\u201D.`:this._carriers?.error||"Loading carriers\u2026"}</div>`}
            ${M.more?A`<div class="opt-empty">Type to search ${M.more} more.</div>`:l}
          </div>`:l}
    </div>`}_renderAdd(){let C=this._form,H=this._entries,V=j2(C.number),M=V.length>=6?t5(this._carriers,V):[],r=C.carrier||M[0]||"",e=this._carriers?.list||{},i=e[r],t=i?.extra?u1[i.extra]||u1[1]:null,p=!!(C.carrier&&M.length&&!M.includes(C.carrier)),n=C5(this._iconRules,C.description),d=C.icon||n,a=[n,...this._iconChoices.filter(o=>o!==n)].slice(0,9);C.icon&&!a.includes(C.icon)&&(a[a.length-1]=C.icon);let m=H.find(o=>o.entry_id===C.entryId)||H[0],x=m?.adds_left??20,s=V.length>=5&&!!r&&C.description.trim().length>0&&(!t||C.extra.trim().length>0)&&x>0,c={number:C.number.replace(/\s+/g,""),carrier:r,valid:s,entryId:m?.entry_id},g=r&&!C.carrierEditing;return A`
      <div class="scrim top" @click=${this._closeAdd}></div>
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="add-title" novalidate @submit=${o=>this._submitAdd(o,c)}>
        <header>
          <div><h2 id="add-title">Add a package</h2><p class="dsub">Paste a tracking number and give it a name.</p></div>
          <button type="button" class="icon-btn" aria-label="Close" @click=${this._closeAdd}>${Z(v.close)}</button>
        </header>
        <div class="form">
          ${C.error?A`<div class="form-error" role="alert">${Z(v.warn,"sm")}<span>${C.error}</span></div>`:l}
          ${H.length>1?A`<div class="field"><label for="f-entry">Parcel account</label>
                <select id="f-entry" class="input" .value=${m?.entry_id||""} @change=${o=>this._setForm({entryId:o.target.value})}>
                  ${H.map(o=>A`<option value=${o.entry_id} ?selected=${o.entry_id===m?.entry_id}>${o.title}</option>`)}
                </select></div>`:l}
          <div class="field">
            <label for="f-number">${t?.number||"Tracking number"}</label>
            <input id="f-number" class="input xl mono" autocomplete="off" autocapitalize="characters" spellcheck="false"
              placeholder="1Z 999 AA1 01 2345 6784" .value=${C.number}
              @input=${o=>this._setForm({number:o.target.value,carrier:"",carrierEditing:!1,extra:"",error:""})}>
          </div>
          ${V.length<6?A`<p class="help">The carrier is recognized from the number. Parcel supports ${Object.keys(e).length||"hundreds of"} carriers.</p>`:g?A`<div class="carrier-row ${p?"warn":""}">
                  ${Z(p?v.warn:v.checkCircle,"sm")}
                  <span class="cr-text"><span>${C.carrier?"Carrier: ":"Looks like "}<b>${this._carrierName(r)}</b></span>
                    ${p?A`<span class="cr-warn">This number doesn’t match the usual format. Rejected tries still count toward today’s limit.</span>`:l}</span>
                  <button type="button" class="btn text sm" @click=${()=>{this._setForm({carrierEditing:!0}),this.updateComplete.then(()=>this.renderRoot.querySelector("#f-carrier")?.focus())}}>Change</button>
                </div>`:this._renderCarrierCombo(C,M,i)}
          ${t?A`<div class="field">
                <label for="f-extra">${t.label}</label>
                <input id="f-extra" class="input" type=${t.type} autocomplete=${t.autocomplete} placeholder=${t.placeholder}
                  .value=${C.extra} @input=${o=>this._setForm({extra:o.target.value})}>
                <p class="help">${this._carrierName(r)} needs this to look up the package.</p>
              </div>`:l}
          <div class="field">
            <label for="f-desc">Name</label>
            <div class="desc-row">
              <span class="desc-av" aria-hidden="true">${b(d)}</span>
              <input id="f-desc" class="input" maxlength="80" placeholder="e.g. Coffee grinder"
                .value=${C.description} @input=${o=>this._setForm({description:o.target.value})}>
            </div>
            <div class="icon-row" role="group" aria-label="Icon">${a.map(o=>A`<button type="button" class="ic-choice" aria-pressed=${String(o===d)} aria-label=${Q[o]||o} title=${Q[o]||o}
                @click=${()=>this._setForm({icon:o})}>${b(o,"sm")}</button>`)}</div>
            <p class="help">Shown here and in the Parcel app. The icon is matched to words in the name; pick another if it doesn’t fit.</p>
          </div>
          <label class="toggle-row" for="f-push">
            <span><span class="toggle-title">Confirm on my phone</span>
              <span class="help">Parcel sends a notification to your devices when the package is added.</span></span>
            <input id="f-push" type="checkbox" class="switch" .checked=${C.push} @change=${o=>this._setForm({push:o.target.checked})}>
          </label>
        </div>
        <footer>
          <span class="quota" title="Parcel allows 20 new packages a day through its API, rejected tries included.">${x} of ${m?.adds_limit??20} adds left today</span>
          <button type="button" class="btn text" @click=${this._closeAdd}>Cancel</button>
          <button type="submit" class="btn filled" ?disabled=${!s||C.submitting}>${C.submitting?"Adding\u2026":"Start tracking"}</button>
        </footer>
      </form>`}};M1(K,"properties",{hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1},_payload:{state:!0},_subError:{state:!0},_query:{state:!0},_searchOpen:{state:!0},_selectedUid:{state:!0},_showAllEvents:{state:!0},_iconsOpen:{state:!0},_menuFor:{state:!0},_confirmFor:{state:!0},_deleting:{state:!0},_addOpen:{state:!0},_form:{state:!0},_carriers:{state:!0},_toast:{state:!0},_refreshing:{state:!0},_tick:{state:!0},_roadWidth:{state:!0}}),M1(K,"styles",A5);customElements.get("parcel-packages-panel")||customElements.define("parcel-packages-panel",K);
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
