import type { NamedBean } from '../context/bean';
import { BeanStub } from '../context/beanStub';
import type { AgColumn } from '../entities/agColumn';
import type { AgProvidedColumnGroup } from '../entities/agProvidedColumnGroup';
import type { ColDef, ColGroupDef, ColKey } from '../entities/colDef';
import type { GridOptions } from '../entities/gridOptions';
import type { ColumnEventType } from '../events';
import type { PropertyChangedEvent, PropertyValueChangedEvent } from '../gridOptionsService';
/** @internal AG_GRID_INTERNAL - Not for public use. Can change / be removed at any time. */
export declare class ColumnModel extends BeanStub implements NamedBean {
    beanName: "colModel";
    pivotMode: boolean;
    colSpanActive: boolean;
    ready: boolean;
    /** Suppresses row model refreshes during batch column state dispatching. */
    changeEventsDispatching: boolean;
    showingPivotResult: boolean;
    /** >0 inside a {@link beginColBatch}/{@link endColBatch} pair: cols services defer their flush to the outermost close. */
    private colBatchDepth;
    /** Set when a staged change needs a display rebuild; consumed (cleared) once by {@link performRefresh}. */
    private pendingRefresh;
    /** A batched `buildFromColDefs` already raised `columnEverythingChanged`; stops the batch flush re-raising it. */
    private everythingChangedInBatch;
    colsList: AgColumn[];
    colsTree: (AgColumn | AgProvidedColumnGroup)[];
    colsTreeDepth: number;
    colDefList: AgColumn[];
    colDefTree: (AgColumn | AgProvidedColumnGroup)[];
    colDefTreeDepth: number;
    private colDefHasMarryChildren;
    hasMarryChildren: boolean;
    /** Single source of truth for `getCol`. Pivot result colIds are namespaced (`pivot_…`). */
    colsById: {
        [id: string]: AgColumn;
    };
    colDefGroupsById: Map<string, AgProvidedColumnGroup>;
    /** Primary cols keyed by colId / userProvidedColDef ref / field; passed back for next-build reuse. */
    private colDefColsByKey;
    /** Every primary group (padding + non-padding) — sweep uses this to find orphans whose parent's
     *  `.children` was reassigned. */
    private colDefAllGroups;
    /** Non-padding displayed groups by `groupId`. Pivot mode = pivot's groups; else = colDefGroupsById. */
    colsGroupsById: Map<string, AgProvidedColumnGroup>;
    /** Every displayed group — padding groups carry `displayInstances` */
    colsAllGroups: AgProvidedColumnGroup[];
    /** Lazy fallback for ColDef-shaped keys not in `colsById`: by-ref (merged + user colDef) plus
     *  `field` when distinct from colId (first-write-wins). */
    private cachedColsByDef;
    private cachedAllCols;
    /** Cache for getColsInStateOrder (pivot only). Invalidated on `colsList` mutation — ref equality
     *  can't substitute, as `moveColumns` reorders in place. */
    private cachedColsInStateOrder;
    /** Prior display order per mode, as colId snapshots, so the next refresh can restore user moves. */
    private lastOrder;
    private lastPivotOrder;
    /** Set when colsList order changes; {@link ensureColsListIndex} re-stamps `colsListIndex` lazily. */
    private colsListIndexDirty;
    /** User provided column definitions */
    colDefs: (ColDef | ColGroupDef)[] | undefined;
    private buildTokenCounter;
    /** Persistent padding-group cache for hierarchy virtual cols, handed to each column-tree build
     *  so `(col, depth)`-stable wrappers survive rebuilds. Owns the padding-group bean lifecycle. */
    private hierarchyWrapperCache;
    postConstruct(): void;
    destroy(): void;
    nextBuildToken(): number;
    isPivotActive(): boolean;
    getCols(): AgColumn[];
    /** Every column known to the grid (user, hierarchy, service, pivot result) in display (`colsList`)
     *  order, with parked pivot primaries appended. Lazily computed on first read after invalidation. */
    getAllCols(): AgColumn[];
    /** Resolve a provided group by id, falling back to parked primaries while pivoting (mirrors `getCol`). */
    getColGroup(groupId: string): AgProvidedColumnGroup | undefined;
    /** Columns in column-state order: hidden pivot primaries first, then `colsList`. Must not be mutated. */
    getColsInStateOrder(): AgColumn[];
    /** `newColDefs`: true = colDefs changed (order restored only with `maintainColumnOrder`); false =
     *  dynamic refresh with unchanged colDefs (prior order restored). */
    private buildFromColDefs;
    /** Open a column-change batch; mutations until the {@link endColBatch} share one flush. */
    beginColBatch(): void;
    /** Close a {@link beginColBatch}; the outermost close flushes once (one source for the whole action). */
    endColBatch(source: ColumnEventType): void;
    /** Refresh once (if needed) + dispatch each touched service. Fires immediately, or defers to {@link endColBatch}
     *  when batched. `refresh` accumulates into {@link pendingRefresh}: membership passes `true`, order/aggFunc-only
     *  (`moveColumn`/`setColumnAggFunc`) pass `false` to dispatch without a rebuild. */
    flushColChanges(source: ColumnEventType, refresh: boolean): void;
    refreshCols(newColDefs: boolean, source: ColumnEventType): void;
    /** Refresh state derived from `colsList` (group + quick-filter cols, colSpan/autoHeight flags) and
     *  reset displayed-col + viewport caches, ahead of `visibleCols.refresh`. Shared by full refreshCols
     *  and by a visibility-only change (which leaves `colsList` unchanged, so skips the rebuild). */
    refreshColsDerivedState(): void;
    /** Single pass: set `colSpanActive` and `rowAutoHeight.active` from `colsList`. */
    private computeColSpanAndAutoHeight;
    /** Full refresh (rebuild cols + recompute visible); immediate, or deferred to {@link endColBatch} when batched. */
    refreshAll(source: ColumnEventType): void;
    private performRefresh;
    /** Reorder `colDefList` only — `newList` MUST be a permutation of the existing col instances
     *  (caller owns the invariant). A full refresh should follow to propagate to display cols.
     *  `colsById` unchanged; `getAllCols` is order-agnostic. */
    replaceColDefList(newList: AgColumn[]): void;
    private setPivotMode;
    recreateColumnDefs(e: PropertyChangedEvent | PropertyValueChangedEvent<keyof GridOptions>): void;
    setColumnDefs(columnDefs: (ColDef | ColGroupDef)[], source: ColumnEventType): void;
    /** Full structural rebuild from current `colDefs` + all contributors (hierarchy, calc cols, …).
     *  Used by contributors whose mutation changes tree structure (e.g. calc-col add/update/remove). */
    rebuildCols(source: ColumnEventType): void;
    /** Mark `AgColumn.colsListIndex` stale — called when `colsList`'s order changes outside a refresh
     *  (`moveColumns`, `applyColumnState` with `applyOrder`); next `ensureColsListIndex` re-stamps. */
    markColsListIndexDirty(): void;
    /** Lazily stamp each col's index in `colsList` onto `AgColumn.colsListIndex`, once per order change.
     *  Readers (e.g. `getColumnDefs`) call this before reading `col.colsListIndex`, so a burst of moves
     *  costs one O(N) pass on the next read, not one per move. */
    ensureColsListIndex(): void;
    /** Resolve any key (colId string, AgColumn, or ColDef) to its current AgColumn. Fast path inline:
     *  string colId, or object whose `colId` hits `colsById` (O(1)); misses delegate to `getColFallback`. */
    getCol(key: ColKey | null | undefined): AgColumn | undefined;
    /** Slow-path fallback for `getCol`: ColDef/ColGroupDef ref lookup + `field`-string fallback, building
     *  the lazy `colsByDef` map on first use. Stale AgColumn refs return `undefined` (unregistered, no `field`). */
    private getColFallback;
    /** Find a column excluding pivot result cols. `pivotKeys` (grid-set) is an O(1) discriminator
     *  standing in for a `pivotCols`-membership test, so `getColumnDefs()` doesn't round-trip them. */
    getNonPivotCol(key: ColKey): AgColumn | undefined;
    /** Like `getNonPivotCol` for hot paths where the key is a known colId string — skips the type-check + field-fallback. */
    getNonPivotColById(key: string): AgColumn | undefined;
    private loadColsByDef;
}
