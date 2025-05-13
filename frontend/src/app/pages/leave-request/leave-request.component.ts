import { Leave, Document, LeaveBalance } from '../../models/leave.model';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { LeaveService } from '../../shared/services/leave.service';
import { AuthService } from '../../shared/services/auth.service';
import { Component, OnInit, ViewChild } from '@angular/core';
import { DxFormComponent } from 'devextreme-angular/ui/form';
import { saveAs } from 'file-saver';
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
import { BytesPipe } from '../../pipes/bytes.pipe';

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
    DxToastModule,
    BytesPipe
  ],
})
export class LeaveRequestComponent implements OnInit {
  @ViewChild(DxFormComponent) leaveForm!: DxFormComponent;
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

  constructor(
    private leaveService: LeaveService,
    private authService: AuthService,
    private sanitizer: DomSanitizer
  ) { }

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
      this.uploadedFiles = e.value;
      this.leave.documents = this.uploadedFiles.map((file, index) => ({
        id: index.toString(), // Temporary ID until server assigns a real one
        name: file.name,
        type: file.type,
        fileType: file.type,
        size: file.size,
        uploadDate: new Date()
      }));
    }
  }

  // Convert document URL to safe URL for viewing
  getSafeUrl(url: string): SafeUrl {
    return this.sanitizer.bypassSecurityTrustUrl(url);
  }

  // Remove document from list
  removeDocument(index: number): void {
    if (this.leave.documents && index >= 0 && index < this.leave.documents.length) {
      const document = this.leave.documents[index];
      if (document.id) {
        // If this is an existing document (not a new upload), try to delete it from server
        if (this.leave.id && !document.id.startsWith('temp_')) {
          this.leaveService.deleteLeaveDocument(this.leave.id, document.id)
            .catch(error => {
              console.error('Error deleting document:', error);
              this.showToast('Error deleting document', 'error');
            });
        }
      }
      this.leave.documents.splice(index, 1);
      this.uploadedFiles = this.uploadedFiles.filter((_, i) => i !== index);
    }
  }

  // Download document
  async downloadDocument(document: Document): Promise<void> {
    try {
      const response = await this.leaveService.downloadLeaveDocument(this.leave.id!, document.id!.toString());
      const blob = new Blob([response], { type: document.fileType });
      saveAs(blob, document.name);
    } catch (error) {
      this.showToast('Error downloading document', 'error');
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
    this.submitting = true;

    try {
      const user = await this.authService.getUser();
      if (!user.isOk || !user.data?.id) {
        throw new Error('User ID not found');
      }

      // Get the leave type ID from the selected leave type
      const leaveTypeId = this.getLeaveTypeId(this.leave.leaveType);
      if (!leaveTypeId) {
        throw new Error('Invalid leave type selected');
      }

      // First create the leave request without documents
      const leaveData = {
        employeeId: user.data.id,
        leave_type_id: leaveTypeId,
        start_date: this.leave.startDate.toISOString().split('T')[0],
        end_date: this.leave.endDate.toISOString().split('T')[0],
        comments: this.leave.comments || '',
        status: 'pending'
      };

      // Create the leave request
      const response = await this.leaveService.createLeaveRequest(leaveData);
      this.leave.id = response.id;

      // Now upload any attached documents
      if (response.id && this.uploadedFiles.length > 0) {
        for (const file of this.uploadedFiles) {
          const result = await this.leaveService.uploadLeaveDocument(this.leave.id, file);
          if (result.id) {
            this.leave.documents.push({
              id: result.id,
              name: file.name,
              fileType: file.type,
              size: file.size,
              uploadDate: new Date()
            });
          }
        }
      }

      this.showToast('Leave request submitted successfully', 'success');
      this.uploadedFiles = [];
      this.leave = {
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
    } catch (error: any) {
      let errorMessage = 'Error submitting leave request';
      if (error && typeof error === 'object' && 'detail' in error.error) {
        errorMessage = `Error: ${error.error.detail}`;
      }
      this.showToast(errorMessage, 'error');
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
