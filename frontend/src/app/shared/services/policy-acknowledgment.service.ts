import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PolicyAcknowledment {
  id: string;
  policy_id: string;
  user_id: string;
  acknowledged_at: string;
  ip_address?: string;
  user_agent?: string;
  signature_data?: string;
  signature_method: string;
  notification_sent_at?: string;
  notification_read_at?: string;
  reminder_count: string;
  is_acknowledged: boolean;
  acknowledgment_deadline?: string;
  created_at: string;
  updated_at?: string;
  policy_name?: string;
  user_name?: string;
  user_email?: string;
}

export interface PolicyAcknowledmentCreate {
  policy_id: string;
  user_id: string;
  signature_data?: string;
  signature_method?: string;
  ip_address?: string;
  user_agent?: string;
}

export interface UserPolicyStatus {
  policy_id: string;
  policy_name: string;
  policy_description?: string;
  file_name: string;
  file_type: string;
  created_at: string;
  acknowledgment_deadline?: string;
  is_acknowledged: boolean;
  acknowledged_at?: string;
  notification_sent_at?: string;
  is_overdue: boolean;
  days_remaining?: number;
}

export interface PolicyAcknowledmentStats {
  policy_id: string;
  policy_name: string;
  total_users: number;
  acknowledged_count: number;
  pending_count: number;
  overdue_count: number;
  acknowledgment_rate: number;
  created_at: string;
}

export interface PolicyNotificationRequest {
  policy_id: string;
  user_ids?: string[];
  deadline_days: number;
}

@Injectable({
  providedIn: 'root'
})
export class PolicyAcknowledmentService {
  private API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('user_token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  async acknowledgePolicy(acknowledgmentData: PolicyAcknowledmentCreate): Promise<PolicyAcknowledment> {
    try {
      const response = await firstValueFrom(
        this.http.post<PolicyAcknowledment>(`${this.API_URL}/policy-acknowledgments/acknowledge`, acknowledgmentData, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async getUserPolicyStatus(): Promise<UserPolicyStatus[]> {
    try {
      const response = await firstValueFrom(
        this.http.get<UserPolicyStatus[]>(`${this.API_URL}/policy-acknowledgments/user/policies`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async sendPolicyNotifications(notificationRequest: PolicyNotificationRequest): Promise<any> {
    try {
      const response = await firstValueFrom(
        this.http.post(`${this.API_URL}/policy-acknowledgments/notify`, notificationRequest, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async getPolicyAcknowledmentStats(policyId: string): Promise<PolicyAcknowledmentStats> {
    try {
      const response = await firstValueFrom(
        this.http.get<PolicyAcknowledmentStats>(`${this.API_URL}/policy-acknowledgments/policy/${policyId}/stats`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async getPolicyAcknowledments(policyId: string): Promise<PolicyAcknowledment[]> {
    try {
      const response = await firstValueFrom(
        this.http.get<PolicyAcknowledment[]>(`${this.API_URL}/policy-acknowledgments/policy/${policyId}/acknowledgments`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  // Helper methods
  isOverdue(deadline?: string): boolean {
    if (!deadline) return false;
    return new Date() > new Date(deadline);
  }

  getDaysRemaining(deadline?: string): number | null {
    if (!deadline) return null;
    const now = new Date();
    const deadlineDate = new Date(deadline);
    const diffTime = deadlineDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  }

  getStatusColor(status: UserPolicyStatus): string {
    if (status.is_acknowledged) return '#28a745'; // Green
    if (status.is_overdue) return '#dc3545'; // Red
    return '#ffc107'; // Yellow
  }

  getStatusText(status: UserPolicyStatus): string {
    if (status.is_acknowledged) return 'Acknowledged';
    if (status.is_overdue) return 'Overdue';
    return 'Pending';
  }

  getStatusIcon(status: UserPolicyStatus): string {
    if (status.is_acknowledged) return 'dx-icon-check';
    if (status.is_overdue) return 'dx-icon-warning';
    return 'dx-icon-clock';
  }
}