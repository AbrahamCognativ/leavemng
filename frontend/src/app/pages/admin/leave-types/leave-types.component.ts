import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { LeaveService } from '../../../shared/services/leave.service';
import { DxiItemModule } from 'devextreme-angular/ui/nested';

// Default leave types matching backend LeaveCodeEnum
const DEFAULT_LEAVE_TYPES = [
  { code: 'annual', description: 'Annual Leave', default_allocation_days: 19 },
  { code: 'sick', description: 'Sick Leave', default_allocation_days: 45 },
  { code: 'maternity', description: 'Maternity Leave', default_allocation_days: 90 },
  { code: 'paternity', description: 'Paternity Leave', default_allocation_days: 14 },
  { code: 'compassionate', description: 'Compassionate Leave', default_allocation_days: 10 },
  { code: 'unpaid', description: 'Unpaid Leave', default_allocation_days: 0 }
];


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
    DxiItemModule
  ]
})
export class LeaveTypesComponent implements OnInit {
  readonly DEFAULT_LEAVE_TYPES = DEFAULT_LEAVE_TYPES;
  leaveTypes: any[] = [];
  leavePolicies: any[] = [];
  isLoading: boolean = false;
  isTypePopupVisible: boolean = false;
  isPolicyPopupVisible: boolean = false;
  isDeleteDialogVisible: boolean = false;
  selectedType: any = null;
  selectedPolicy: any = null;
  leaveTypeToDelete: any = null;
  orgUnits: any[] = [];
  accrualFrequencies = [
    { id: 'monthly', text: 'Monthly' },
    { id: 'quarterly', text: 'Quarterly' },
    { id: 'yearly', text: 'Yearly' },
    { id: 'one_time', text: 'One Time' }
  ];
  availableCodes = [
    { value: 'annual', text: 'Annual Leave' },
    { value: 'sick', text: 'Sick Leave' },
    { value: 'unpaid', text: 'Unpaid Leave' },
    { value: 'compassionate', text: 'Compassionate Leave' },
    { value: 'maternity', text: 'Maternity Leave' },
    { value: 'paternity', text: 'Paternity Leave' },
    { value: 'custom', text: 'Custom Leave Type' }
  ];

  typeFormData: any = {
    code: null,
    description: '',
    default_allocation_days: 0
  };
  
  // Updated onTypeAdd method to use custom code for new types
  onTypeAdd = () => {
    this.selectedType = null;
    this.typeFormData = {
      code: 'custom', // Default to custom for new types
      description: '',
      default_allocation_days: 0
    };
    this.isTypePopupVisible = true;
  }
  
  // Updated onTypeEdit method
  onTypeEdit = (e: any) => {
    this.selectedType = e.row?.data || e.data;
    
    // Make sure we have valid data before setting typeFormData
    if (this.selectedType) {
      this.typeFormData = { 
        code: this.selectedType.code || 'custom',
        description: this.selectedType.description || '',
        default_allocation_days: this.selectedType.default_allocation_days || 0
      };
    } else {
      this.typeFormData = {
        code: 'custom',
        description: '',
        default_allocation_days: 0
      };
    }
    
    this.isTypePopupVisible = true;
  }

  policyFormData: any = {
    org_unit_id: null,
    leave_type_id: null,
    allocation_days_per_year: 0,
    accrual_frequency: 'monthly',
    accrual_amount_per_period: 0
  };

  constructor(private leaveService: LeaveService) {
    // Bind component methods to ensure proper 'this' context
    this.saveType = this.saveType.bind(this);
    this.savePolicy = this.savePolicy.bind(this);
    this.confirmDelete = this.confirmDelete.bind(this);
    this.cancelDelete = this.cancelDelete.bind(this);
  }

  ngOnInit() {
    this.loadData();
  }

  async loadData() {
    try {
      this.isLoading = true;
      this.leaveTypes = await this.leaveService.getLeaveTypes();
      
      const existingCodes = new Set(this.leaveTypes.map(t => t.code));
      
      // Create only missing leave types
      for (const type of DEFAULT_LEAVE_TYPES) {
        if (!existingCodes.has(type.code)) {
          await this.leaveService.createLeaveType(type);
        }
      }
      
      this.leaveTypes = await this.leaveService.getLeaveTypes();
      this.leavePolicies = await this.leaveService.getLeavePolicies();
      this.orgUnits = await this.leaveService.getOrgUnits();
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      this.isLoading = false;
    }
  }

  onPolicyAdd = () => {
    this.policyFormData = {
      org_unit_id: null,
      leave_type_id: null,
      allocation_days_per_year: 0,
      accrual_frequency: 'monthly',
      accrual_amount_per_period: 0
    };
    this.isPolicyPopupVisible = true;
  }

  onPolicyEdit = (e: any) => {
    this.selectedPolicy = e.data;
    this.policyFormData = { ...e.data };
    this.isPolicyPopupVisible = true;
  }

  async saveType() {
    try {
      this.isLoading = true;
  
      // Store a reference to the service to avoid "this" context issues
      const leaveService = this.leaveService;
      if (!leaveService) {
        throw new Error('Leave service is not available');
      }
  
      // Make sure typeFormData is initialized
      if (!this.typeFormData) {
        this.typeFormData = {
          code: 'custom', // Default to custom
          description: '',
          default_allocation_days: 0
        };
      }
  
      // Validate required fields
      if (!this.typeFormData.code) {
        throw new Error('Leave type code is required');
      }
      
      if (!this.typeFormData.description) {
        throw new Error('Leave type description is required');
      }
      
      // Ensure the code is one of the valid enum values
      const validCodes = ['annual', 'sick', 'unpaid', 'compassionate', 'maternity', 'paternity', 'custom'];
      if (!validCodes.includes(this.typeFormData.code)) {
        throw new Error('Invalid leave type code. Must be one of: ' + validCodes.join(', '));
      }
      
      // Convert to number to avoid sending string values for numeric fields
      this.typeFormData.default_allocation_days = 
        Number(this.typeFormData.default_allocation_days) || 0;
  
      // Prepare data to send
      const dataToSend = {
        code: this.typeFormData.code,
        description: this.typeFormData.description,
        default_allocation_days: this.typeFormData.default_allocation_days
      };
  
      if (this.selectedType) {
        await leaveService.updateLeaveType(this.selectedType.id, dataToSend);
      } else {
        await leaveService.createLeaveType(dataToSend);
      }
      await this.loadData();
      this.isTypePopupVisible = false;
      this.selectedType = null;
    } catch (error: any) {
      console.error('Error saving leave type:', error);
      
      // Better error handling for API validation errors
      if (error.error?.detail) {
        // Format validation errors for display
        const validationErrors = error.error.detail.map((err: any) => {
          return `${err.loc[1]}: ${err.msg}`;
        }).join('\n');
        alert(`Validation error:\n${validationErrors}`);
      } else {
        alert(error.message || 'Error saving leave type');
      }
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

  deleteType = (e: any) => {
    this.leaveTypeToDelete = e.row?.data || e.data;
    this.isDeleteDialogVisible = true;
  }

  async confirmDelete() {
    if (this.leaveTypeToDelete) {
      try {
        const leaveService = this.leaveService;
        if (!leaveService) {
          throw new Error('Leave service is not available');
        }

        this.isLoading = true;
        await leaveService.deleteLeaveType(this.leaveTypeToDelete.id);
        await this.loadData();
      } catch (error: any) {
        console.error('Error deleting leave type:', error);
        alert(error.message || 'Error deleting leave type');
      } finally {
        this.isLoading = false;
        this.isDeleteDialogVisible = false;
        this.leaveTypeToDelete = null;
      }
    }
  }

  cancelDelete() {
    this.isDeleteDialogVisible = false;
    this.leaveTypeToDelete = null;
  }

  async deletePolicy(e: any) {
    try {
      const leaveService = this.leaveService;
      if (!leaveService) {
        throw new Error('Leave service is not available');
      }

      this.isLoading = true;
      await leaveService.deleteLeavePolicy(e.data.id);
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