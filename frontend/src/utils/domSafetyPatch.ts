/**
 * React 19 + ECharts 切视图时偶发 removeChild/insertBefore 对孤儿节点抛错。
 * 在 createRoot 前打补丁：父节点上无此子节点时跳过并告警，避免整页崩溃。
 */
export function applyReactDomSafetyPatch(): void {
  if (typeof Node === 'undefined') return;
  const proto = Node.prototype;

  const originalRemoveChild = proto.removeChild;
  proto.removeChild = function patchedRemoveChild<T extends Node>(child: T): T {
    if (child.parentNode !== this) {
      console.warn('[domSafetyPatch] removeChild skipped: node is not a child of this node');
      return child;
    }
    return originalRemoveChild.call(this, child) as T;
  };

  const originalInsertBefore = proto.insertBefore;
  proto.insertBefore = function patchedInsertBefore<T extends Node>(
    newNode: T,
    referenceNode: Node | null,
  ): T {
    if (referenceNode && referenceNode.parentNode !== this) {
      console.warn('[domSafetyPatch] insertBefore: reference not a child, appending instead');
      return originalInsertBefore.call(this, newNode, null) as T;
    }
    return originalInsertBefore.call(this, newNode, referenceNode) as T;
  };
}
