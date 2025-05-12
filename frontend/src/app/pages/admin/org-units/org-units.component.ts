import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxToolbarModule } from 'devextreme-angular/ui/toolbar';
import { OrgUnitService, OrgUnit } from '../../../shared/services/org-unit.service';
import { DxiItemModule } from 'devextreme-angular/ui/nested';

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
    DxiItemModule
  ]
})
export class OrgUnitsComponent implements OnInit {
  orgUnits: OrgUnit[] = [];
  isLoading: boolean = false;
  isPopupVisible: boolean = false;
  selectedUnit: OrgUnit | null = null;
  formData: Partial<OrgUnit> = {
    name: '',
    parent_unit_id: undefined
  };

  constructor(private orgUnitService: OrgUnitService) {}

  ngOnInit() {
    this.loadData();
  }

  async loadData() {
    try {
      this.isLoading = true;
      this.orgUnits = await this.orgUnitService.getOrgUnits();
    } catch (error) {
      console.error('Error loading organization units:', error);
    } finally {
      this.isLoading = false;
    }
  }

  onAdd() {
    this.formData = {
      name: '',
      parent_unit_id: undefined
    };
    this.selectedUnit = null;
    this.isPopupVisible = true;
  }

  onEdit(e: any) {
    this.selectedUnit = e.data;
    this.formData = { ...e.data };
    this.isPopupVisible = true;
  }

  async save() {
    try {
      this.isLoading = true;
      if (this.selectedUnit) {
        await this.orgUnitService.updateOrgUnit(this.selectedUnit.id, this.formData);
      } else {
        await this.orgUnitService.createOrgUnit(this.formData);
      }
      await this.loadData();
      this.isPopupVisible = false;
    } catch (error) {
      console.error('Error saving organization unit:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async delete(e: any) {
    try {
      this.isLoading = true;
      await this.orgUnitService.deleteOrgUnit(e.data.id);
      await this.loadData();
    } catch (error) {
      console.error('Error deleting organization unit:', error);
    } finally {
      this.isLoading = false;
    }
  }

  getParentName(parentId: string | undefined): string {
    if (!parentId) return 'None';
    if (!this.orgUnits || this.orgUnits.length === 0) return '';
    const parent = this.orgUnits.find(u => u.id === parentId);
    return parent ? parent.name : 'Unknown';
  }
}