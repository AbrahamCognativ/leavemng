import { Component, NgModule, Output, Input, EventEmitter, ViewChild, ElementRef, AfterViewInit, OnDestroy, OnInit } from '@angular/core';
import { DxTreeViewModule, DxTreeViewComponent, DxTreeViewTypes } from 'devextreme-angular/ui/tree-view';
import { getNavigationItems } from '../../../app-navigation';
import { AuthService, NavigationService } from '../../services';
import * as events from 'devextreme/events';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-side-navigation-menu',
  templateUrl: './side-navigation-menu.component.html',
  styleUrls: ['./side-navigation-menu.component.scss'],
  standalone: false
})
export class SideNavigationMenuComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild(DxTreeViewComponent, { static: true })
  menu!: DxTreeViewComponent;

  @Output()
  selectedItemChanged = new EventEmitter<DxTreeViewTypes.ItemClickEvent>();

  @Output()
  openMenu = new EventEmitter<any>();

  private _selectedItem!: String;
  @Input()
  set selectedItem(value: String) {
    this._selectedItem = value;
    if (!this.menu.instance) {
      return;
    }

    this.menu.instance.selectItem(value);
  }

  private _items!: Record <string, unknown>[];
  private navigationSubscription?: Subscription;

  get items() {
    return this._items || [];
  }

  private _compactMode = false;
  @Input()
  get compactMode() {
    return this._compactMode;
  }
  set compactMode(val) {
    this._compactMode = val;

    if (!this.menu.instance) {
      return;
    }

    if (val) {
      this.menu.instance.collapseAll();
    } else {
      this.menu.instance.expandItem(this._selectedItem);
    }
  }

  constructor(
    private elementRef: ElementRef,
    private authService: AuthService,
    private navigationService: NavigationService
  ) { }

  async ngOnInit() {
    // Subscribe to navigation changes
    this.navigationSubscription = this.navigationService.navigationItems$.subscribe(items => {
      this.updateNavigationItems(items);
    });

    // Initialize navigation
    await this.navigationService.updateNavigation();
  }

  private updateNavigationItems(navigationItems: any[]) {
    // Filter out admin menu items for non-admin users
    const filteredNavigation = this.authService.isAdmin ?
      navigationItems :
      navigationItems.filter(item => item.text !== 'Admin');

    this._items = filteredNavigation.map((item) => {
      if(item.path && !(/^\//.test(item.path))){
        item.path = `/${item.path}`;
      }
      return { ...item, expanded: false } // Always start with collapsed dropdowns
    });

    // Refresh the tree view if it exists
    if (this.menu?.instance) {
      this.menu.instance.option('items', this._items);
      // Collapse all items to ensure dropdowns are closed
      this.menu.instance.collapseAll();
    }
  }

  onItemClick(event: DxTreeViewTypes.ItemClickEvent) {
    this.selectedItemChanged.emit(event);
  }

  ngAfterViewInit() {
    events.on(this.elementRef.nativeElement, 'dxclick', (e: Event) => {
      this.openMenu.next(e);
    });
  }

  ngOnDestroy() {
    events.off(this.elementRef.nativeElement, 'dxclick');
    if (this.navigationSubscription) {
      this.navigationSubscription.unsubscribe();
    }
  }
}

@NgModule({
  imports: [ DxTreeViewModule ],
  declarations: [ SideNavigationMenuComponent ],
  exports: [ SideNavigationMenuComponent ]
})
export class SideNavigationMenuModule { }
