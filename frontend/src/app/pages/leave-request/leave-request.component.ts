import { Leave, Document, LeaveBalance } from '../../models/leave.model';
import { LeaveService } from '../../shared/services/leave.service';
import { AuthService } from '../../shared/services/auth.service';
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxFileUploaderModule } from 'devextreme-angular/ui/file-uploader';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxDateBoxModule } from 'devextreme-angular/ui/date-box';
import { DxTextAreaModule } from 'devextreme-angular/ui/text-area';
import { DxiItemModule, DxoLabelModule, DxiValidationRuleModule } from 'devextreme-angular/ui/nested';
import { DxToastModule } from 'devextreme-angular/ui/toast';

@Component({
  selector: 'app-leave-request',
  templateUrl: './leave-request.component.html',
  styleUrls: ['./leave-request.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxFormModule,
    DxButtonModule,
    DxiItemModule,
    DxoLabelModule,
    DxFileUploaderModule,
    DxLoadIndicatorModule,
    DxSelectBoxModule,
    DxDateBoxModule,
    DxTextAreaModule,
    DxiValidationRuleModule,
    DxToastModule
  ],
})
export class LeaveRequestComponent implements OnInit {
  leaveTypes: any[] = [];
  leaveTypesDescription: string[] = [];
  leaveBalances: LeaveBalance[] = [];
  leave: Leave = {
    id: '',
    employeeId: '',
    leaveType: '',
    startDate: new Date(),
    endDate: new Date(),
    comments: '',
    status: 'pending',
    documents: [],
    createdAt: new Date(),
    updatedAt: new Date()
  };

  uploadedFiles: File[] = [];
  submitting = false;
  calculatedDays = 0;
  minDate = new Date();
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';

  constructor(private leaveService: LeaveService, private authService: AuthService) { }

  ngOnInit(): void {
    this.loadLeaveTypes();
    this.loadLeaveBalances();
  }

  async loadLeaveTypes(): Promise<void> {
    try {
      const types = await this.leaveService.getLeaveTypes();
      this.leaveTypesDescription = types.map(type => type.description);
      this.leaveTypes = types;
    } catch (error) {
      this.showToast('Error loading leave types', 'error');
    }
  }

  async loadLeaveBalances(): Promise<void> {
    try {
      const leaveTypes = await this.leaveService.getLeaveTypes();
      const user = await this.authService.getUser();
      if(user.isOk){
        const userId = user.data?.id;
        if(userId){
          const userLeaveData = await this.leaveService.getUserLeave(userId);
          for(const balance of userLeaveData.leave_balance){
            const leaveType = leaveTypes.find(type => type.code === balance.leave_type);
            balance.leave_type = leaveType?.description || 'Unknown';
            balance.total_days = leaveType?.default_allocation_days || 0;
            balance.balance_days = balance.balance_days || 0;
          }
          this.leaveBalances = userLeaveData.leave_balance;
        }
      }      
    } catch (error) {
      this.showToast('Error loading leave balances', 'error');
    }
  }

  onFileUploaded(e: any): void {
    if (e.value && e.value.length > 0) {
      const newDocuments = Array.from(e.value as File[]).map((file: File) => {
        return {
          name: file.name,
          fileType: file.type,
          size: file.size,
          file: file,
          uploadDate: new Date()
        } as Document;
      });

      if (!this.leave.documents) {
        this.leave.documents = [];
      }

      this.leave.documents = [...this.leave.documents, ...newDocuments];
    }
  }

  async removeDocument(index: number): Promise<void> {
    if (this.leave.documents && this.leave.documents.length > index) {
      const document = this.leave.documents[index];
      if (document.id) {
        try {
          await this.leaveService.deleteLeaveDocument(this.leave.id.toString(), document.id.toString());
        } catch (error) {
          this.showToast('Error deleting document', 'error');
          return;
        }
      }
      this.leave.documents.splice(index, 1);
      this.leave.documents = [...this.leave.documents];
    }
  }

  async calculateWorkingDays(): Promise<void> {
    if (this.leave.startDate && this.leave.endDate) {
      try {
        const start = new Date(this.leave.startDate);
        const end = new Date(this.leave.endDate);
        let days = 0;
        const current = new Date(start);
        
        while (current <= end) {
          const day = current.getDay();
          if (day !== 0 && day !== 6) { // Skip weekends
            days++;
          }
          current.setDate(current.getDate() + 1);
        }
        
        this.calculatedDays = days;
      } catch (error) {
        this.showToast('Error calculating working days', 'error');
      }
    }
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  async onSubmit(): Promise<void> {
    if (this.submitting) return;
  
    if (this.leave.startDate > this.leave.endDate) {
      this.showToast('End date cannot be before start date', 'error');
      return;
    }
  
    await this.calculateWorkingDays();
    const user = await this.authService.getUser();
    if(user.isOk){
      const userId = user.data?.id;
      if(userId){
        this.leave.employeeId = userId;
      }
    }
    this.submitting = true;
    try {
      const payload = {
        employeeId: this.leave.employeeId,
        leave_type_id: this.getLeaveTypeId(this.leave.leaveType), 
        start_date: this.leave.startDate.toISOString().split('T')[0],
        end_date: this.leave.endDate.toISOString().split('T')[0],
        comments: this.leave.comments,
        status: this.leave.status,
        documents: this.leave.documents,
        createdAt: this.leave.createdAt.toISOString(),
        updatedAt: this.leave.updatedAt.toISOString(),
      };
      console.log("payload", payload);
      const response = await this.leaveService.createLeaveRequest(payload);
      console.log("response", response);
      this.showToast('Leave request submitted successfully!', 'success');
      this.resetForm();
      await this.loadLeaveBalances();
    } catch (error: any) {
      this.showToast('Error submitting leave request', 'error');
    } finally {
      this.submitting = false;
    }
  }

  resetForm(): void {
    this.leave = {
      id: '',
      employeeId: this.leave.employeeId,
      leaveType: '',
      startDate: new Date(),
      endDate: new Date(),
      comments: '',
      status: 'pending',
      documents: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.uploadedFiles = [];
    this.calculatedDays = 0;
  }

  getLeaveTypeId(leaveTypeName: string): string {
    const found = this.leaveTypes.find(t => t.description === leaveTypeName);
    if(found){
      return found.id;
    }
    return '';
  }
  
}
