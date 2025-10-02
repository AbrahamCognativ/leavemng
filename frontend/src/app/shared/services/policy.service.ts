import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Policy {
  id: string;
  name: string;
  description?: string;
  file_name: string;
  file_type: string;
  file_size?: string;
  org_unit_id?: string;
  org_unit_name?: string;
  creator_name: string;
  created_at: string;
  updated_at?: string;
}

export interface PolicyCreate {
  name: string;
  description?: string;
  org_unit_id?: string;
}

export interface PolicyUpdate {
  name?: string;
  description?: string;
  org_unit_id?: string;
}

@Injectable({
  providedIn: 'root'
})
export class PolicyService {
  private API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('user_token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  async getPolicies(orgUnitId?: string): Promise<Policy[]> {
    try {
      let url = `${this.API_URL}/policies`;
      if (orgUnitId) {
        url += `?org_unit_id=${orgUnitId}`;
      }
      
      const response = await firstValueFrom(
        this.http.get<Policy[]>(url, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async getPolicy(policyId: string): Promise<Policy> {
    try {
      const response = await firstValueFrom(
        this.http.get<Policy>(`${this.API_URL}/policies/${policyId}`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async createPolicy(policyData: PolicyCreate, file: File): Promise<Policy> {
    try {
      const formData = new FormData();
      formData.append('name', policyData.name);
      if (policyData.description) {
        formData.append('description', policyData.description);
      }
      if (policyData.org_unit_id) {
        formData.append('org_unit_id', policyData.org_unit_id);
      }
      formData.append('file', file);

      const response = await firstValueFrom(
        this.http.post<Policy>(`${this.API_URL}/policies`, formData, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async updatePolicy(policyId: string, policyData: PolicyUpdate): Promise<Policy> {
    try {
      const response = await firstValueFrom(
        this.http.put<Policy>(`${this.API_URL}/policies/${policyId}`, policyData, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async deletePolicy(policyId: string): Promise<void> {
    try {
      await firstValueFrom(
        this.http.delete(`${this.API_URL}/policies/${policyId}`, {
          headers: this.getAuthHeaders()
        })
      );
    } catch (error) {
      throw error;
    }
  }

  async downloadPolicy(policyId: string, fileName: string): Promise<void> {
    try {
      const token = localStorage.getItem('user_token');
      if (!token) {
        throw new Error('Authentication token not found');
      }

      // Use token parameter instead of Authorization header for downloads
      const downloadUrl = `${this.API_URL}/policies/${policyId}/download?token=${encodeURIComponent(token)}`;
      
      // Create a temporary link to trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = fileName;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      throw error;
    }
  }

  getPolicyViewUrl(policyId: string): string {
    const token = localStorage.getItem('user_token');
    if (!token) {
      throw new Error('Authentication token not found');
    }
    return `${this.API_URL}/policies/${policyId}/download?token=${encodeURIComponent(token)}&inline=true`;
  }

  getPolicyPreviewUrl(policyId: string): string {
    const token = localStorage.getItem('user_token');
    if (!token) {
      throw new Error('Authentication token not found');
    }
    return `${this.API_URL}/policies/${policyId}/preview?token=${encodeURIComponent(token)}`;
  }

  async viewPolicyInline(policyId: string): Promise<Blob> {
    try {
      const response = await firstValueFrom(
        this.http.get(`${this.API_URL}/policies/${policyId}/download?inline=true`, {
          headers: this.getAuthHeaders(),
          responseType: 'blob'
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  getFileIcon(fileType: string): string {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return 'dx-icon-doc';
      case 'doc':
      case 'docx':
        return 'dx-icon-doc';
      case 'ppt':
      case 'pptx':
        return 'dx-icon-doc';
      case 'jpg':
      case 'jpeg':
      case 'png':
        return 'dx-icon-image';
      default:
        return 'dx-icon-doc';
    }
  }

  getFileTypeColor(fileType: string): string {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return '#dc3545';
      case 'doc':
      case 'docx':
        return '#0d6efd';
      case 'ppt':
      case 'pptx':
        return '#fd7e14';
      case 'jpg':
      case 'jpeg':
      case 'png':
        return '#198754';
      default:
        return '#6c757d';
    }
  }
}