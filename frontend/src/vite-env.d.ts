/// <reference types="vite/client" />

// remark-gfm 未随包提供 TypeScript 类型声明（TS7016），
// 这里补充最小模块声明以通过 tsc --noEmit 类型检查。
declare module 'remark-gfm';
