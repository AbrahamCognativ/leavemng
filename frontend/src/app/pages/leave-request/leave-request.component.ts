import { Leave, Document } from '../../models/leave.model';
import { LeaveService } from '../../leave.service';
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
    DxiValidationRuleModule
  ],
})
export class LeaveRequestComponent implements OnInit {
  leaveTypes = [
    'Annual Leave',
    'Sick Leave',
    'Maternity Leave',
    'Paternity Leave',
    'Compassionate Leave',
    'Study Leave',
    'Unpaid Leave'
  ];

  leaveBalances = [
    { type: 'Annual Leave', available: 20, total: 25 },
    { type: 'Sick Leave', available: 10, total: 10 },
    { type: 'Study Leave', available: 5, total: 5 }
  ];

  leave: Leave = {
    id: 0,
    employeeId: 0,
    leaveType: '',
    startDate: new Date(),
    endDate: new Date(),
    reason: '',
    status: 'pending',
    documents: [],
    createdAt: new Date(),
    updatedAt: new Date()
  };

  uploadedFiles: File[] = [];
  submitting = false;
  calculatedDays = 0;
  minDate = new Date();

  constructor(private leaveService: LeaveService) { }

  ngOnInit(): void {
    // Get the current employee ID from a service or authentication context
    this.leave.employeeId = this.leaveService.getCurrentEmployeeId();

    // Load leave balances for the current employee
    this.loadLeaveBalances();
  }

  loadLeaveBalances(): void {
    this.leaveService.getEmployeeLeaveBalances(this.leave.employeeId).subscribe({
      next: (balances) => {
        if (balances) {
          this.leaveBalances = balances;
        }
      },
      error: (err) => {
        console.error('Error loading leave balances:', err);
      }
    });
  }

  onFileUploaded(e: any): void {
    if (e.value && e.value.length > 0) {
      // Map File objects to our Document model
      const newDocuments = Array.from(e.value as File[]).map((file: File) => {
        return {
          name: file.name,
          fileType: file.type,
          size: file.size,
          file: file,
          uploadDate: new Date()
        } as Document;
      });

      // Add to existing documents
      if (!this.leave.documents) {
        this.leave.documents = [];
      }

      this.leave.documents = [...this.leave.documents, ...newDocuments];
    }
  }

  removeDocument(index: number): void {
    if (this.leave.documents && this.leave.documents.length > index) {
      this.leave.documents.splice(index, 1);
      // Create a new array reference to trigger change detection
      this.leave.documents = [...this.leave.documents];
    }
  }

  calculateWorkingDays(): void {
    if (this.leave.startDate && this.leave.endDate) {
      this.leaveService.calculateWorkingDays(this.leave.startDate, this.leave.endDate)
        .subscribe(days => {
          this.calculatedDays = days;
        });
    }
  }

  onSubmit(): void {
    if (this.submitting) return;

    // Validate dates
    if (this.leave.startDate > this.leave.endDate) {
      alert('End date cannot be before start date');
      return;
    }

    // Calculate the working days
    this.calculateWorkingDays();

    this.submitting = true;
    this.leaveService.createLeave(this.leave).subscribe({
      next: (response) => {
        // Show success notification
        this.leaveService.showNotification({
          message: 'Leave request submitted successfully!',
          type: 'success',
          duration: 5000
        });

        // Reset the form
        this.resetForm();

        // Refresh leave balances
        this.loadLeaveBalances();
      },
      error: (err) => {
        this.leaveService.showNotification({
          message: 'Error submitting leave request: ' + err.message,
          type: 'error',
          duration: 5000
        });
      },
      complete: () => {
        this.submitting = false;
      }
    });
  }

  resetForm(): void {
    this.leave = {
      id: 0,
      employeeId: this.leave.employeeId,
      leaveType: '',
      startDate: new Date(),
      endDate: new Date(),
      reason: '',
      status: 'pending',
      documents: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.uploadedFiles = [];
    this.calculatedDays = 0;
  }
}
