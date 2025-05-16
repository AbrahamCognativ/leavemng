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
import { Router } from '@angular/router';

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
  leaveTypeCodeMap: {[code: string]: number} = {};
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
    private sanitizer: DomSanitizer,
    private router: Router
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

      if (user.isOk) {
        const userId = user.data?.id;

        if (userId) {
          const userLeaveData = await this.leaveService.getUserLeave(userId);

          if (userLeaveData.leave_balance) {
            // First, prepare a dictionary to track used days for each leave type code
            const usedDaysByCode: {[code: string]: number} = {};

            // If there are leave requests, calculate used days for each leave type
            if (userLeaveData.leave_request && userLeaveData.leave_request.length > 0) {
              for (const request of userLeaveData.leave_request) {
                if (request.leave_type && request.total_days) {
                  // Get current used days for this leave type, or initialize to 0
                  const currentUsed = usedDaysByCode[request.leave_type] || 0;
                  // Add days from this request to the accumulated total
                  usedDaysByCode[request.leave_type] = currentUsed + request.total_days;
                }
              }
            }
            this.leaveTypeCodeMap = usedDaysByCode;
            // Now process each balance with the accumulated days
            for (const balance of userLeaveData.leave_balance) {
              const leaveTypeCode = balance.leave_type;
              const leaveType = leaveTypes.find(type => type.code === leaveTypeCode);

              // Set leave type description and total days
              balance.leave_type = leaveType?.description || 'Unknown';
              balance.total_days = leaveType?.default_allocation_days || 0;

              // Get accumulated used days for this leave type
              const usedDays = usedDaysByCode[leaveTypeCode] || 0;

              // Calculate remaining balance
              balance.balance_days = balance.total_days - usedDays;
            }
          } else {
            // Initialize empty leave balance array if none exists
            userLeaveData.leave_balance = [];
          }

          this.leaveBalances = userLeaveData.leave_balance;
        }
      }
    } catch (error) {
      console.error('Error loading leave balances:', error);
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
      // Validate form
      if (!this.leaveForm.instance.validate().isValid) {
        this.showToast('Please fill in all required fields correctly', 'error');
        this.submitting = false;
        return;
      }

      // Get user data
      const user = await this.authService.getUser();
      if (!user.isOk || !user.data?.id) {
        throw new Error('User ID not found');
      }

      // Get selected leave type
      const leaveType = this.getLeaveType(this.leave.leaveType);
      if (!leaveType || !leaveType.id) {
        throw new Error('Invalid leave type selected');
      }

      console.log('Selected leave type:', leaveType);

      // Format dates properly for the API
      const startDate = this.formatDateForAPI(this.leave.startDate);
      const endDate = this.formatDateForAPI(this.leave.endDate);

      // Prepare leave request data - ONLY include fields that the backend schema expects
      const leaveData = {
        leave_type_id: leaveType.id,
        start_date: startDate,
        end_date: endDate,
        comments: this.leave.comments || '',
        total_days: this.calculatedDays
        // Don't include user_id or status - backend will set these automatically
      };

      console.log('Submitting leave request with data:', leaveData);

      // Check leave balance
      var daysCount = this.leave.endDate.getTime() - this.leave.startDate.getTime();
      daysCount = daysCount / (1000 * 60 * 60 * 24);
      const leaveBalance = this.leaveBalances.find(b => b.leave_type === leaveType.description);
      
      if (!leaveBalance) {
        this.showToast(`No leave balance found for ${leaveType.description}`, 'error');
        this.submitting = false;
        return;
      }
      
      if (daysCount > leaveBalance.balance_days) {
        this.showToast(`Leave balance not enough for ${leaveType.description}. Available: ${leaveBalance.balance_days} days`, 'error');
        this.submitting = false;
        return;
      }

      // Step 1: Create the leave request
      const response = await this.leaveService.createLeaveRequest(leaveData);
      console.log('Leave request created successfully:', response);
      
      if (!response || !response.id) {
        throw new Error('Failed to create leave request - no ID returned');
      }
      
      this.leave.id = response.id;

      // Step 2: Upload any attached documents
      let uploadSuccess = true;
      let failedUploads: string[] = [];
      
      if (response.id && this.uploadedFiles.length > 0) {
        console.log(`Uploading ${this.uploadedFiles.length} documents for leave request ${response.id}`);
        
        for (const file of this.uploadedFiles) {
          try {
            console.log(`Uploading file: ${file.name}`);
            console.log(`Uploading file ${file.name} to leave request ${response.id}`);
            const result = await this.leaveService.uploadLeaveDocument(response.id, file);
            console.log('Document upload result:', result);
            
            // The backend returns document_id in the response
            if (result && (result.document_id || result.id)) {
              const docId = result.document_id || result.id;
              console.log(`Document uploaded successfully with ID: ${docId}`);
              
              this.leave.documents.push({
                id: docId,
                name: file.name,
                fileType: file.type,
                size: file.size,
                uploadDate: new Date()
              });
            } else {
              console.error('Document upload failed - no document ID in response', result);
              uploadSuccess = false;
              failedUploads.push(file.name);
            }
          } catch (uploadError) {
            console.error('Error uploading document:', uploadError);
            uploadSuccess = false;
            failedUploads.push(file.name);
          }
        }
      }

      // Show appropriate success message
      if (uploadSuccess) {
        this.showToast('Leave request submitted successfully', 'success');
      } else {
        this.showToast(`Leave request created but some documents failed to upload: ${failedUploads.join(', ')}`, 'warning');
      }
      
      // Reset form and navigate away
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
      this.router.navigate(['/dashboard']);
    } catch (error: any) {
      console.error('Leave request submission error:', error);
      let errorMessage = 'Error submitting leave request';
      
      if (error && typeof error === 'object') {
        if (error.error && typeof error.error === 'object' && 'detail' in error.error) {
          errorMessage = `Error: ${error.error.detail}`;
        } else if (error.message) {
          errorMessage = `Error: ${error.message}`;
        }
      }
      
      this.showToast(errorMessage, 'error');
    } finally {
      this.submitting = false;
    }
  }
  
  // Helper method to format dates in YYYY-MM-DD format
  private formatDateForAPI(date: Date): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toISOString().split('T')[0]; // Returns YYYY-MM-DD
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

  getLeaveType(leaveTypeName: string): any {
    const found = this.leaveTypes.find(t => t.description === leaveTypeName);
    if(found){
      return found;
    }
    return null;
  }

}
