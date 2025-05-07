import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxToolbarModule } from 'devextreme-angular/ui/toolbar';
import { LeaveService } from '../../../shared/services/leave.service';
import { DxiItemModule } from 'devextreme-angular/ui/nested';

@Component({
  selector: 'app-leave-types',
  templateUrl: './leave-types.component.html',
  styleUrls: ['./leave-types.component.scss'],
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
export class LeaveTypesComponent implements OnInit {
  leaveTypes: any[] = [];
  leavePolicies: any[] = [];
  isLoading: boolean = false;
  isTypePopupVisible: boolean = false;
  isPolicyPopupVisible: boolean = false;
  selectedType: any = null;
  selectedPolicy: any = null;
  orgUnits: any[] = [];
  accrualFrequencies = [
    { id: 'monthly', text: 'Monthly' },
    { id: 'quarterly', text: 'Quarterly' },
    { id: 'yearly', text: 'Yearly' },
    { id: 'one_time', text: 'One Time' }
  ];

  typeFormData: any = {
    code: '',
    description: '',
    default_allocation_days: 0
  };

  policyFormData: any = {
    org_unit_id: null,
    leave_type_id: null,
    allocation_days_per_year: 0,
    accrual_frequency: 'monthly',
    accrual_amount_per_period: 0
  };

  constructor(private leaveService: LeaveService) {}

  ngOnInit() {
    this.loadData();
  }

  async loadData() {
    try {
      this.isLoading = true;
      this.leaveTypes = await this.leaveService.getLeaveTypes();
      this.leavePolicies = await this.leaveService.getLeavePolicies();
      this.orgUnits = await this.leaveService.getOrgUnits();
      console.log("leavePolicies", this.leavePolicies);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      this.isLoading = false;
    }
  }

  onTypeAdd() {
    this.typeFormData = {
      code: '',
      description: '',
      default_allocation_days: 0
    };
    this.isTypePopupVisible = true;
  }

  onPolicyAdd() {
    this.policyFormData = {
      org_unit_id: null,
      leave_type_id: null,
      allocation_days_per_year: 0,
      accrual_frequency: 'monthly',
      accrual_amount_per_period: 0
    };
    this.isPolicyPopupVisible = true;
  }

  onTypeEdit(e: any) {
    this.selectedType = e.data;
    this.typeFormData = { ...e.data };
    this.isTypePopupVisible = true;
  }

  onPolicyEdit(e: any) {
    this.selectedPolicy = e.data;
    this.policyFormData = { ...e.data };
    this.isPolicyPopupVisible = true;
  }

  async saveType() {
    try {
      this.isLoading = true;
      if (this.selectedType) {
        await this.leaveService.updateLeaveType(this.selectedType.id, this.typeFormData);
      } else {
        await this.leaveService.createLeaveType(this.typeFormData);
      }
      await this.loadData();
      this.isTypePopupVisible = false;
    } catch (error) {
      console.error('Error saving leave type:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async savePolicy() {
    try {
      this.isLoading = true;
      if (this.selectedPolicy) {
        await this.leaveService.updateLeavePolicy(this.selectedPolicy.id, this.policyFormData);
      } else {
        await this.leaveService.createLeavePolicy(this.policyFormData);
      }
      await this.loadData();
      this.isPolicyPopupVisible = false;
    } catch (error) {
      console.error('Error saving leave policy:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async deleteType(e: any) {
    try {
      this.isLoading = true;
      await this.leaveService.deleteLeaveType(e.data.id);
      await this.loadData();
    } catch (error) {
      console.error('Error deleting leave type:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async deletePolicy(e: any) {
    try {
      this.isLoading = true;
      await this.leaveService.deleteLeavePolicy(e.data.id);
      await this.loadData();
    } catch (error) {
      console.error('Error deleting leave policy:', error);
    } finally {
      this.isLoading = false;
    }
  }

  getOrgUnitName = (data: any) => {
    const unit = this.orgUnits.find(u => u.id === data.org_unit_id);
    return unit ? unit.name : data.org_unit_id;
  }

  getLeaveTypeName = (data: any) => {
    const type = this.leaveTypes.find(t => t.id === data.leave_type_id);
    return type ? type.description : data.leave_type_id;
  }
} 