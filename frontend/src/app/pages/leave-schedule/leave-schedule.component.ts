import { Component, OnInit, ChangeDetectorRef, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { 
  DxSchedulerModule, 
  DxLoadIndicatorModule, 
  DxButtonModule,
  DxToolbarModule,
  DxTemplateModule,
  DxTooltipModule,
  DxSchedulerComponent
} from 'devextreme-angular';

import { LeaveService } from '../../shared/services/leave.service';

// Define a custom type for the appointment form event
interface AppointmentFormEvent {
  cancel?: boolean;
  component?: any;
  element?: any;
  model?: any;
  form?: any;
  appointmentData?: any;
  [key: string]: any;
}

// Interface for leave request
export interface LeaveRequest {
  id: string;
  text: string;
  startDate: Date;
  endDate: Date;
  allDay: boolean;
  status: string;
  employeeName: string;
  employeeEmail: string;
  leaveType?: string;
  userId?: string;
  description?: string;
}

// Interface for leave request from API
interface ApiLeaveRequest {
  id: string | number;
  title: string;
  start_date: string;
  end_date: string;
  status: 'pending' | 'approved' | 'rejected';
  description?: string;
  employee_name?: string;
  employee_email?: string;
  leave_type?: string;
  all_day?: boolean;
}

@Component({
  selector: 'app-leave-schedule',
  standalone: true,
  imports: [
    CommonModule, 
    DxSchedulerModule,
    DxLoadIndicatorModule,
    DxButtonModule,
    DxToolbarModule,
    DxTemplateModule,
    DxTooltipModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './leave-schedule.component.html',
  styleUrls: ['./leave-schedule.component.scss']
})
export class LeaveScheduleComponent implements OnInit {
  // Component properties with types
  currentDate: Date = new Date();
  currentView: string = 'month';
  views: string[] = ['month']; // Only show month view
  leaveRequests: LeaveRequest[] = [];
  loading = true;
  schedulerHeight = 800;
  
  // Month selector
  months = [
    { name: 'January', value: 0 },
    { name: 'February', value: 1 },
    { name: 'March', value: 2 },
    { name: 'April', value: 3 },
    { name: 'May', value: 4 },
    { name: 'June', value: 5 },
    { name: 'July', value: 6 },
    { name: 'August', value: 7 },
    { name: 'September', value: 8 },
    { name: 'October', value: 9 },
    { name: 'November', value: 10 },
    { name: 'December', value: 11 }
  ];
  
  // Get current month for the selector
  get currentMonth(): number {
    return this.currentDate.getMonth();
  }
  
  // Test data for development
  private testData: LeaveRequest[] = [
    {
      id: '1',
      text: 'Test Leave',
      startDate: new Date(2023, 5, 15, 9, 0),
      endDate: new Date(2023, 5, 17, 18, 0),
      status: 'approved',
      leaveType: 'Annual',
      description: 'Test leave request',
      allDay: true,
      employeeName: 'John Doe',
      employeeEmail: 'john.doe@example.com'
    },
    {
      id: '2',
      text: 'Another Test',
      startDate: new Date(2023, 5, 20, 9, 0),
      endDate: new Date(2023, 5, 22, 18, 0),
      status: 'pending',
      leaveType: 'Sick',
      description: 'Sick leave',
      allDay: true,
      employeeName: 'Jane Smith',
      employeeEmail: 'jane.smith@example.com'
    }
  ];
  
  // Scheduler resources for status colors
  resources: any[] = [
    {
      fieldExpr: 'status',
      dataSource: [
        { id: 'pending', text: 'Pending', color: '#ffc107' },
        { id: 'approved', text: 'Approved', color: '#28a745' },
        { id: 'rejected', text: 'Rejected', color: '#dc3545' }
      ]
    }
  ];
  
  // Scheduler views configuration
  schedulerViews: any = {
    day: { name: 'Day' },
    week: { name: 'Week' },
    month: { name: 'Month' }
  };

  constructor(
    private leaveService: LeaveService,
    private cdr: ChangeDetectorRef
  ) {
    console.log('Scheduler initialized with date:', this.currentDate);
    console.log('Available views:', this.views);
  }

  ngOnInit(): void {
    this.loadLeaveRequests();
  }

  // Toggle the sidebar menu
  toggleSidebar(): void {
    // This is a placeholder - in a real app, you would use a service to communicate with the layout component
    const event = new CustomEvent('toggle-sidebar');
    window.dispatchEvent(event);
  }

  // Process leave requests from API to match scheduler format
  private processLeaveRequests(requests: any[]): LeaveRequest[] {
    if (!requests || !Array.isArray(requests)) {
      console.error('Invalid or empty requests array');
      return [];
    }

    console.log('Processing leave requests:', requests);

    return requests
      .filter(request => {
        // Filter out invalid requests
        const hasRequiredFields = request && 
                                request.id && 
                                request.start_date && 
                                request.end_date &&
                                request.status;
        if (!hasRequiredFields) {
          console.warn('Request missing required fields:', request);
        }
        return hasRequiredFields;
      })
      .map((request) => {
        try {
          // Parse dates
          const startDate = new Date(request.start_date);
          const endDate = new Date(request.end_date);

          // Handle potential invalid dates
          if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
            console.warn('Invalid date in request:', request);
            return null;
          }

          // Adjust end date to be inclusive
          endDate.setHours(23, 59, 59, 999);

          // Get employee details - check different possible locations in the response
          const employeeName = request.employee_name || 
                              request.employee?.full_name || 
                              request.user?.full_name ||
                              request.employeeName ||
                              `User ${request.user_id?.substring(0, 8) || 'Unknown'}`;
          
          const employeeEmail = request.employee_email || 
                              request.employee?.email || 
                              request.user?.email ||
                              request.employeeEmail ||
                              `${request.user_id?.substring(0, 8) || 'unknown'}@example.com`;

          // Create the processed request object
          const processedRequest: LeaveRequest = {
            id: request.id,
            text: employeeEmail || request.title || 'Leave Request',
            startDate: startDate,
            endDate: endDate,
            allDay: request.all_day !== undefined ? request.all_day : true,
            status: (request.status || '').toLowerCase(),
            employeeName: employeeName,
            employeeEmail: employeeEmail,
            leaveType: request.leave_type || request.leave_type_id || 'Unspecified',
            userId: request.user_id || request.userId,
            description: request.comments || request.description
          };

          console.log('Processed request:', processedRequest);
          return processedRequest;
        } catch (error) {
          console.error('Error processing request:', error, 'Request:', request);
          return null;
        }
      })
      .filter((request): request is LeaveRequest => request !== null); // Type guard to filter out nulls type safety
  }

  async loadLeaveRequests(): Promise<void> {
    this.loading = true;
    try {
      // First try to load from API
      console.log('Fetching leave requests from API...');
      const requests = await this.leaveService.getLeaveRequests();
      console.log('Raw API response:', JSON.stringify(requests, null, 2));
      
      this.leaveRequests = this.processLeaveRequests(requests);
      console.log('Processed leave requests:', JSON.stringify(this.leaveRequests, null, 2));
      
      // If no data from API, use test data
      if (this.leaveRequests.length === 0) {
        console.warn('No leave requests found in the database. Using test data.');
        this.leaveRequests = [...this.testData]; // Use test data directly since it's already in the correct format
      }
      
      this.cdr.detectChanges();
    } catch (error) {
      console.error('Error loading leave requests:', error);
      // Fall back to test data if there's an error
      console.warn('Falling back to test data due to error');
      this.leaveRequests = [...this.testData];
      this.cdr.detectChanges();
    } finally {
      this.loading = false;
    }
  }

  // Check if two dates are the same day
  isSameDay(date1: Date, date2: Date): boolean {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
  }

  onAppointmentFormOpening(e: AppointmentFormEvent): void {
    console.log('Appointment form opening event:', e);
    
    if (!e || !e['form']) {
      console.error('Form not available in the event');
      return;
    }
    
    // Make the form read-only
    e.cancel = true;
    
    if (e.appointmentData) {
      console.log('Appointment data:', JSON.stringify(e.appointmentData, null, 2));
      
      // Create a custom popup with the appointment details
      const popup = document.createElement('div');
      popup.className = 'custom-appointment-popup';
      
      // Format dates
      const formatDate = (date: Date | string) => {
        if (!date) return 'N/A';
        const d = new Date(date);
        return d.toLocaleDateString() + (e.appointmentData.allDay ? '' : ' ' + d.toLocaleTimeString());
      };
      
      // Create the popup content
      popup.innerHTML = `
        <div class="popup-header">
          <h3>${e.appointmentData.text || 'Leave Request'}</h3>
          <span class="status-badge status-${e.appointmentData.status}">
            ${e.appointmentData.status?.toUpperCase() || 'PENDING'}
          </span>
        </div>
        <div class="popup-body">
          <div class="detail-row">
            <i class="dx-icon dx-icon-user"></i>
            <div class="detail-content">
              <div class="detail-label">Employee</div>
              <div>${e.appointmentData.employeeName || 'N/A'}</div>
            </div>
          </div>
          <div class="detail-row">
            <i class="dx-icon dx-icon-email"></i>
            <div class="detail-content">
              <div class="detail-label">Email</div>
              <div>
                ${e.appointmentData.employeeEmail ? 
                  `<a href="mailto:${e.appointmentData.employeeEmail}">${e.appointmentData.employeeEmail}</a>` : 
                  'N/A'}
              </div>
            </div>
          </div>
          <div class="detail-row">
            <i class="dx-icon dx-icon-tags"></i>
            <div class="detail-content">
              <div class="detail-label">Leave Type</div>
              <div>${e.appointmentData.leaveType || 'Not specified'}</div>
            </div>
          </div>
          <div class="detail-row">
            <i class="dx-icon dx-icon-clock"></i>
            <div class="detail-content">
              <div class="detail-label">Duration</div>
              <div>
                ${formatDate(e.appointmentData.startDate)}
                ${e.appointmentData.endDate ? ` to ${formatDate(e.appointmentData.endDate)}` : ''}
                ${e.appointmentData.allDay ? ' (All Day)' : ''}
              </div>
            </div>
          </div>
          ${e.appointmentData.description ? `
            <div class="detail-row">
              <i class="dx-icon dx-icon-info"></i>
              <div class="detail-content">
                <div class="detail-label">Notes</div>
                <div class="notes">${e.appointmentData.description}</div>
              </div>
            </div>` : ''}
        </div>
        <div class="popup-footer">
          <button id="closePopup" class="dx-button dx-button-normal">Close</button>
        </div>
      `;
      
      // Add styles
      const style = document.createElement('style');
      style.textContent = `
        .custom-appointment-popup {
          padding: 20px;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          max-width: 400px;
        }
        .popup-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding-bottom: 10px;
          border-bottom: 1px solid #e0e0e0;
        }
        .popup-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 500;
        }
        .status-badge {
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
        }
        .status-pending {
          background-color: #fff3cd;
          color: #856404;
        }
        .status-approved {
          background-color: #d4edda;
          color: #155724;
        }
        .status-rejected {
          background-color: #f8d7da;
          color: #721c24;
        }
        .detail-row {
          display: flex;
          margin-bottom: 12px;
          align-items: flex-start;
        }
        .detail-row i {
          margin-right: 12px;
          color: #6c757d;
          margin-top: 2px;
        }
        .detail-label {
          font-size: 12px;
          color: #6c757d;
          margin-bottom: 2px;
        }
        .notes {
          white-space: pre-wrap;
          background: #f8f9fa;
          padding: 8px;
          border-radius: 4px;
          margin-top: 4px;
        }
        .popup-footer {
          margin-top: 20px;
          text-align: right;
          padding-top: 10px;
          border-top: 1px solid #e0e0e0;
        }
        .dx-button {
          margin-left: 8px;
        }
      `;
      
      // Add close button handler
      setTimeout(() => {
        const closeButton = document.getElementById('closePopup');
        if (closeButton) {
          closeButton.addEventListener('click', () => {
            if (e.component) {
              e.component.hideAppointmentTooltip();
            }
            document.body.removeChild(popup);
            document.head.removeChild(style);
          });
        }
      });
      
      // Add to document
      document.head.appendChild(style);
      document.body.appendChild(popup);
      
      // Position the popup
      if (e.component) {
        const position = e.component.getAppointmentPosition(e.appointmentData, 0, 0);
        if (position) {
          popup.style.position = 'absolute';
          popup.style.left = `${position.left}px`;
          popup.style.top = `${position.top}px`;
          popup.style.zIndex = '100000';
          popup.style.backgroundColor = 'white';
          popup.style.borderRadius = '8px';
          popup.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
          popup.style.maxHeight = '80vh';
          popup.style.overflowY = 'auto';
        }
      }
    }
    
    if (e) {
      e.cancel = true; // Prevent default form
      
      // Show the tooltip instead of the form
      const tooltip = document.querySelector('.dx-tooltip-wrapper.dx-popup-wrapper');
      if (tooltip) {
        console.log('Tooltip element found, showing tooltip');
        // Trigger a mouseover event on the appointment to show the tooltip
        const appointmentElement = document.querySelector(`[data-appointment-id='${e.appointmentData.id}']`);
        if (appointmentElement) {
          appointmentElement.dispatchEvent(new MouseEvent('mouseover'));
        }
      }
    }
  }

  onAppointmentAdded(e: any): void {
    console.log('Appointment added:', e);
    // Here you would typically send the new appointment to your API
    // For now, we'll just log it
  }

  onAppointmentUpdated(e: any): void {
    console.log('Appointment updated:', e);
    // Here you would typically update the appointment in your API
    // For now, we'll just log it
  }

  onAppointmentDeleted(e: any): void {
    console.log('Appointment deleted:', e);
    // Here you would typically delete the appointment from your API
    // For now, we'll just log it
  }
  
  // Handle month change from the selector
  onMonthChanged(e: any): void {
    console.log('Month changed to:', e.value);
    // Update the current date to the first day of the selected month
    const newDate = new Date();
    newDate.setMonth(e.value);
    newDate.setDate(1);
    this.currentDate = newDate;
  }

  // Ensure tooltip has all necessary data
  onTooltipShowing(e: any): void {
    if (!e.appointmentData) {
      console.error('No appointment data in tooltip');
      return;
    }
    
    // Debug log the appointment data
    console.log('Appointment data in tooltip:', {
      id: e.appointmentData.id,
      text: e.appointmentData.text,
      employeeName: e.appointmentData.employeeName,
      employeeEmail: e.appointmentData.employeeEmail,
      startDate: e.appointmentData.startDate,
      endDate: e.appointmentData.endDate,
      status: e.appointmentData.status,
      leaveType: e.appointmentData.leaveType,
      description: e.appointmentData.description,
      allDay: e.appointmentData.allDay
    });
    
    // Ensure required fields have default values
    const data = e.appointmentData;
    data.employeeName = data.employeeName || 'Unknown';
    data.employeeEmail = data.employeeEmail || 'No email';
    data.leaveType = data.leaveType || 'Not specified';
    data.status = (data.status || 'pending').toLowerCase();
    
    // If dates are strings, convert them to Date objects
    if (data.startDate && !(data.startDate instanceof Date)) {
      data.startDate = new Date(data.startDate);
    }
    if (data.endDate && !(data.endDate instanceof Date)) {
      data.endDate = new Date(data.endDate);
    }
  }
}
