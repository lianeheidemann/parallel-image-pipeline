// Number and list formatting shared by the page (pt-BR).
const LOCALE = "pt-BR";
const fixed2 = n => n.toLocaleString(LOCALE,{minimumFractionDigits:2,maximumFractionDigits:2});
export const num = (n,digits=2) => n.toLocaleString(LOCALE,{maximumFractionDigits:digits});
export const integer = n => n.toLocaleString(LOCALE);
export const percent = n => n.toLocaleString(LOCALE,{style:"percent",maximumFractionDigits:0});
export const seconds = n => `${fixed2(n)} s`;
export const times = n => `${fixed2(n)}×`;
// ["2","4","8"] -> "2, 4 e 8"
export const list = items => items.length>1 ? `${items.slice(0,-1).join(", ")} e ${items.at(-1)}` : `${items[0]}`;
