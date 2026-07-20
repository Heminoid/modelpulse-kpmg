import type { BeanCollection } from '../../context/context';
import type { AgProvidedColumnGroup } from '../../entities/agProvidedColumnGroup';
import type { ColumnEventType } from '../../events';
export declare const _getColGroupState: (beans: BeanCollection) => {
    groupId: string;
    open: boolean;
}[];
export declare const _setColGroupOpen: (beans: BeanCollection, key: AgProvidedColumnGroup | string | null | undefined, newValue: boolean, source: ColumnEventType) => void;
export declare const _setColGroupState: (beans: BeanCollection, stateItems: {
    groupId: string;
    open: boolean | undefined;
}[], source: ColumnEventType) => void;
export declare const _resetColGroupState: (beans: BeanCollection, source: ColumnEventType) => void;
