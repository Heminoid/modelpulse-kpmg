import type { NamedBean } from '../context/bean';
import { BeanStub } from '../context/beanStub';
import type { GridBodyCtrl } from '../gridBodyComp/gridBodyCtrl';
import type { RowContainerEventsFeature } from '../gridBodyComp/rowContainer/rowContainerEventsFeature';
import type { AgColumnHeader } from '../headerRendering/cells/column/agColumnHeader';
import type { AgColumnGroupHeader } from '../headerRendering/cells/columnGroup/agColumnGroupHeader';
import type { GridHeaderCtrl } from '../headerRendering/gridHeaderCtrl';
import type { CellMouseListenerFeature } from '../rendering/cell/cellMouseListenerFeature';
export declare class TouchService extends BeanStub implements NamedBean {
    beanName: "touchSvc";
    mockBodyContextMenu(ctrl: GridBodyCtrl, listener: (mouseListener?: MouseEvent, touch?: Touch, touchEvent?: TouchEvent) => void): void;
    mockHeaderContextMenu(ctrl: GridHeaderCtrl, listener: (mouseListener?: MouseEvent, touch?: Touch, touchEvent?: TouchEvent) => void): void;
    mockRowContextMenu(ctrl: RowContainerEventsFeature): void;
    handleCellDoubleClick(ctrl: CellMouseListenerFeature, mouseEvent: MouseEvent): boolean;
    setupForHeader(comp: AgColumnHeader): void;
    setupForHeaderGroup(comp: AgColumnGroupHeader): void;
    setupForHeaderGroupElement(comp: AgColumnGroupHeader, eElement: HTMLElement, action: (event: MouseEvent) => void): void;
    private mockContextMenu;
}
