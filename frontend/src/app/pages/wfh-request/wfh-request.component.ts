import { Component, OnInit, ViewChild } from '@angular/core';
import { DxFormComponent } from 'devextreme-angular/ui/form';
import { CommonModule } from '@angular/common';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxDateBoxModule } from 'devextreme-angular/ui/date-box';
import { DxTextAreaModule } from 'devextreme-angular/ui/text-area';
import { DxiItemModule, DxoLabelModule, DxiValidationRuleModule } from 'devextreme-angular/ui/nested';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { Router } from '@angular/router';
import { WFHService } from '../../shared/services/wfh.service';
import { AuthService } from '../../shared/services/auth.service';

interface WFHRequest {
  id?: string;
  start_date: Date;
  end_date: Date;
  reason?: string;
  status?: string;
  applied_at?: Date;
}

@Component({
  selector: 'app-wfh-request',
  templateUrl: './wfh-request.component.html',
  styleUrls: ['./wfh-request.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxFormModule,
    DxButtonModule,
    DxiItemModule,
    DxoLabelModule,
    DxLoadIndicatorModule,
    DxDateBoxModule,
    DxTextAreaModule,
    DxiValidationRuleModule,
    DxToastModule
  ],
})
export class WFHRequestComponent implements OnInit {
  @ViewChild(DxFormComponent) wfhForm!: DxFormComponent;
  
  wfhRequest: WFHRequest = {
    start_date: new Date(),
    end_date: new Date(),
    reason: '',
    status: 'pending'
  };
  
  submitting = false;
  calculatedDays = 0;
  minDate = new Date();
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';

  constructor(
    private wfhService: WFHService,
    private authService: AuthService,
    private router: Router
  ) {
    // Set minimum date to 14 days from now
    this.minDate.setDate(this.minDate.getDate() + 14);
  }

  ngOnInit(): void {
    this.calculateWorkingDays();
  }

  async calculateWorkingDays(): Promise<void> {
    if (this.wfhRequest.start_date && this.wfhRequest.end_date) {
      try {
        const start = new Date(this.wfhRequest.start_date);
        const end = new Date(this.wfhRequest.end_date);
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
      if (!this.wfhForm.instance.validate().isValid) {
        this.showToast('Please fill in all required fields correctly', 'error');
        this.submitting = false;
        return;
      }

      // Get user data
      const user = await this.authService.getUser();
      if (!user.isOk || !user.data?.id) {
        throw new Error('User ID not found');
      }

      // Format dates properly for the API
      const startDate = this.formatDateForAPI(this.wfhRequest.start_date);
      const endDate = this.formatDateForAPI(this.wfhRequest.end_date);

      // Prepare WFH request data
      const wfhData = {
        start_date: startDate,
        end_date: endDate,
        reason: this.wfhRequest.reason || ''
      };

      // Create the WFH request
      const response = await this.wfhService.createWFHRequest(wfhData);

      if (!response || !response.id) {
        throw new Error('Failed to create WFH request - no ID returned');
      }

      this.showToast('Work from home request submitted successfully', 'success');

      // Reset form and navigate away
      this.wfhRequest = {
        start_date: new Date(),
        end_date: new Date(),
        reason: '',
        status: 'pending'
      };
      
      // Navigate to dashboard after a short delay
      setTimeout(() => {
        this.router.navigate(['/dashboard']);
      }, 1500);

    } catch (error: any) {
      let errorMessage = 'Error submitting work from home request';

      if (error && typeof error === 'object') {
        if (error.error && typeof error.error === 'object' && 'detail' in error.error) {
          // Handle Pydantic validation errors (array format)
          if (Array.isArray(error.error.detail)) {
            const validationErrors = error.error.detail.map((err: any) => {
              if (err.loc && err.msg) {
                const field = err.loc[err.loc.length - 1]; // Get the field name
                return `${field}: ${err.msg}`;
              }
              return err.msg || 'Validation error';
            });
            errorMessage = `Validation Error: ${validationErrors.join(', ')}`;
          } else {
            errorMessage = `Error: ${error.error.detail}`;
          }
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
    this.wfhRequest = {
      start_date: new Date(),
      end_date: new Date(),
      reason: '',
      status: 'pending'
    };
    this.calculatedDays = 0;
  }

  // Validation function for start date
  validateStartDate = (params: any) => {
    if (!params.value) {
      return true; // Let required validation handle empty values
    }
    
    const selectedDate = new Date(params.value);
    const fourteenDaysFromNow = new Date();
    fourteenDaysFromNow.setDate(fourteenDaysFromNow.getDate() + 14);
    fourteenDaysFromNow.setHours(0, 0, 0, 0);
    
    return selectedDate >= fourteenDaysFromNow;
  }

  // Validation function for end date
  validateEndDate = (params: any) => {
    if (!this.wfhRequest.start_date || !params.value) {
      return true; // Let required validation handle empty values
    }
    
    const startDate = new Date(this.wfhRequest.start_date);
    const endDate = new Date(params.value);
    
    return endDate >= startDate;
  }

  // Event handler for date changes
  onStartDateChanged(): void {
    this.calculateWorkingDays();
  }

  onEndDateChanged(): void {
    this.calculateWorkingDays();
  }

  // Custom validation function for reason length
  validateReasonLength = (params: any) => {
    const value = params.value || '';
    const currentLength = value.length;
    
    if (currentLength < 40) {
      const needed = 40 - currentLength;
      return {
        isValid: false,
        message: `Reason must be at least 40 characters long. Current: ${currentLength} characters, ${needed} more needed.`
      };
    }
    
    return { isValid: true };
  }
}