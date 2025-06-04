import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxToolbarModule } from 'devextreme-angular/ui/toolbar';
import { DxTreeViewModule } from 'devextreme-angular/ui/tree-view';
import { OrgUnitService, OrgUnit, TreeItem } from '../../../shared/services/org-unit.service';
import { DxiItemModule } from 'devextreme-angular/ui/nested';
import { Subscription, forkJoin } from 'rxjs';
import { ItemClickEvent } from 'devextreme/ui/tree_view';
import { UserService, IUser } from '../../../shared/services/user.service';

@Component({
  selector: 'app-org-units',
  templateUrl: './org-units.component.html',
  styleUrls: ['./org-units.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxLoadIndicatorModule,
    DxFormModule,
    DxButtonModule,
    DxPopupModule,
    DxToolbarModule,
    DxTreeViewModule,
    DxiItemModule
  ]
})
export class OrgUnitsComponent implements OnInit, OnDestroy {
  orgUnits: OrgUnit[] = [];
  orgTree: TreeItem[] = [];
  isLoading: boolean = false;
  isPopupVisible: boolean = false;
  isUserPopupVisible: boolean = false;
  selectedUnit: OrgUnit | null = null;
  selectedUser: IUser | null = null;
  formData: Partial<OrgUnit> = {
    name: '',
    parent_unit_id: undefined
  };
  userFormData: Partial<IUser> = {};
  managers: IUser[] = [];
  private subscriptions: Subscription[] = [];

  constructor(
    private orgUnitService: OrgUnitService,
    private userService: UserService
  ) {}

  ngOnInit() {
    this.loadData();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  loadData() {
    this.isLoading = true;
    const subscription = forkJoin({
      units: this.orgUnitService.getOrgUnits(),
      tree: this.orgUnitService.getOrgChart()
    }).subscribe({
      next: (result) => {
        this.orgUnits = result.units;
        this.orgTree = this.processTreeItems(result.tree);
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading organization units:', error);
        this.isLoading = false;
      }
    });
    this.subscriptions.push(subscription);
  }

  private processTreeItems(items: TreeItem[]): TreeItem[] {
    // Find root items (items without parent_unit_id)
    const rootItems = items.filter(item => !item.parent_unit_id);
    
    // If there's only one root item, expand it and its immediate children
    if (rootItems.length === 1) {
      return items.map(item => {
        if (!item.parent_unit_id) {
          // Root item - expand it
          return {
            ...item,
            expanded: true,
            children: item.children?.map(child => ({
              ...child,
              expanded: false // Keep children collapsed
            }))
          };
        }
        return {
          ...item,
          expanded: false // Keep all other items collapsed
        };
      });
    }
    
    // If there are multiple root items, keep them all collapsed
    return items.map(item => ({
      ...item,
      expanded: false
    }));
  }

  onAdd() {
    this.formData = {
      name: '',
      parent_unit_id: undefined
    };
    this.selectedUnit = null;
    this.isPopupVisible = true;
  }

  onEdit(unit: OrgUnit) {
    this.selectedUnit = unit;
    this.formData = { ...unit };
    this.isPopupVisible = true;
  }

  onUserClick(user: IUser) {
    this.selectedUser = user;
    this.userFormData = { ...user };
    this.loadManagers();
    this.isUserPopupVisible = true;
  }

  loadManagers() {
    const subscription = this.userService.getUsers().subscribe({
      next: (users: IUser[]) => {
        this.managers = users.filter(user => user.role_title?.toLowerCase().includes('manager'));
      },
      error: (error: any) => {
        console.error('Error loading managers:', error);
      }
    });
    this.subscriptions.push(subscription);
  }

  save() {
    this.isLoading = true;
    const request = this.selectedUnit
      ? this.orgUnitService.updateOrgUnit(this.selectedUnit.id, this.formData)
      : this.orgUnitService.createOrgUnit(this.formData);

    const subscription = request.subscribe({
      next: () => {
        this.loadData();
        this.isPopupVisible = false;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error saving organization unit:', error);
        this.isLoading = false;
      }
    });
    this.subscriptions.push(subscription);
  }

  saveUser() {
    if (this.selectedUser) {
      const subscription = this.userService.updateUser(this.selectedUser.id, this.userFormData)
        .subscribe({
          next: () => {
            this.isUserPopupVisible = false;
            this.loadData();
          },
          error: (error: any) => {
            console.error('Error updating user:', error);
          }
        });
      this.subscriptions.push(subscription);
    }
  }

  delete(e: any) {
    this.isLoading = true;
    const subscription = this.orgUnitService.deleteOrgUnit(e.data.id).subscribe({
      next: () => {
        this.loadData();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error deleting organization unit:', error);
        this.isLoading = false;
      }
    });
    this.subscriptions.push(subscription);
  }

  getParentName(parentId: string | undefined): string {
    if (!parentId) return 'None';
    if (!this.orgUnits || this.orgUnits.length === 0) return '';
    const parent = this.orgUnits.find(u => u.id === parentId);
    return parent ? parent.name : 'Unknown';
  }

  getManagerNames(managers: any[]): string {
    return managers.map(m => m.name).join(', ');
  }

  onTreeItemClick(e: ItemClickEvent) {
    if (e.itemData && e.itemData['type'] === 'unit') {
      const item = e.itemData as TreeItem;
      this.selectedUnit = {
        id: item.id,
        name: item.name,
        parent_unit_id: item.parent_unit_id
      };
      this.formData = { ...this.selectedUnit };
      this.isPopupVisible = true;
    }
  }
}