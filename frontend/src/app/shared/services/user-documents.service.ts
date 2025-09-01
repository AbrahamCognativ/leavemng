import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface UserDocument {
  id: string;
  name: string;
  description?: string;
  file_name: string;
  file_type: string;
  file_size?: string;
  document_type?: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  creator_name?: string;
  email_sent_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface MyDocument {
  id: string;
  name: string;
  description?: string;
  file_name: string;
  file_type: string;
  file_size?: string;
  document_type?: string;
  created_at: string;
  creator_name: string;
}

export interface UserDocumentCreate {
  name: string;
  description?: string;
  user_id: string;
  document_type?: string;
  send_email_notification?: boolean;
}

export interface UserDocumentUpdate {
  name?: string;
  description?: string;
  document_type?: string;
}

export interface UserDocumentStats {
  total_documents: number;
  documents_by_type: { [key: string]: number };
  recent_uploads: number;
  total_users_with_documents: number;
}

@Injectable({
  providedIn: 'root'
})
export class UserDocumentsService {
  private API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('user_token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  // Admin/HR/Manager methods
  async getUserDocuments(userId?: string, documentType?: string): Promise<UserDocument[]> {
    try {
      let url = `${this.API_URL}/user-documents`;
      const params = new URLSearchParams();
      
      if (userId) {
        params.append('user_id', userId);
      }
      if (documentType) {
        params.append('document_type', documentType);
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await firstValueFrom(
        this.http.get<UserDocument[]>(url, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async getUserDocument(documentId: string): Promise<UserDocument> {
    try {
      const response = await firstValueFrom(
        this.http.get<UserDocument>(`${this.API_URL}/user-documents/${documentId}`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async createUserDocument(documentData: UserDocumentCreate, file: File): Promise<UserDocument> {
    try {
      const formData = new FormData();
      formData.append('name', documentData.name);
      formData.append('user_id', documentData.user_id);
      
      if (documentData.description) {
        formData.append('description', documentData.description);
      }
      if (documentData.document_type) {
        formData.append('document_type', documentData.document_type);
      }
      if (documentData.send_email_notification !== undefined) {
        formData.append('send_email_notification', documentData.send_email_notification.toString());
      }
      formData.append('file', file);

      const response = await firstValueFrom(
        this.http.post<UserDocument>(`${this.API_URL}/user-documents`, formData, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async updateUserDocument(documentId: string, documentData: UserDocumentUpdate): Promise<UserDocument> {
    try {
      const response = await firstValueFrom(
        this.http.put<UserDocument>(`${this.API_URL}/user-documents/${documentId}`, documentData, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  async deleteUserDocument(documentId: string): Promise<void> {
    try {
      await firstValueFrom(
        this.http.delete(`${this.API_URL}/user-documents/${documentId}`, {
          headers: this.getAuthHeaders()
        })
      );
    } catch (error) {
      throw error;
    }
  }

  async getUserDocumentStats(): Promise<UserDocumentStats> {
    try {
      const response = await firstValueFrom(
        this.http.get<UserDocumentStats>(`${this.API_URL}/user-documents/stats/overview`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  // User methods
  async getMyDocuments(): Promise<MyDocument[]> {
    try {
      const response = await firstValueFrom(
        this.http.get<MyDocument[]>(`${this.API_URL}/user-documents/my-documents`, {
          headers: this.getAuthHeaders()
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  // Download and preview methods
  async downloadDocument(documentId: string, fileName: string): Promise<void> {
    try {
      const token = localStorage.getItem('user_token');
      if (!token) {
        throw new Error('Authentication token not found');
      }
      
      const response = await firstValueFrom(
        this.http.get(`${this.API_URL}/user-documents/${documentId}/download?token=${encodeURIComponent(token)}`, {
          responseType: 'blob'
        })
      );

      // Create blob link to download
      const url = window.URL.createObjectURL(response);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      throw error;
    }
  }

  getDocumentViewUrl(documentId: string): string {
    const token = localStorage.getItem('user_token');
    if (!token) {
      throw new Error('Authentication token not found');
    }
    return `${this.API_URL}/user-documents/${documentId}/download?token=${encodeURIComponent(token)}&inline=true`;
  }

  getDocumentPreviewUrl(documentId: string): string {
    const token = localStorage.getItem('user_token');
    if (!token) {
      throw new Error('Authentication token not found');
    }
    return `${this.API_URL}/user-documents/${documentId}/preview?token=${encodeURIComponent(token)}`;
  }

  async viewDocumentInline(documentId: string): Promise<Blob> {
    try {
      const response = await firstValueFrom(
        this.http.get(`${this.API_URL}/user-documents/${documentId}/download?inline=true`, {
          headers: this.getAuthHeaders(),
          responseType: 'blob'
        })
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  // Utility methods
  getFileIcon(fileType: string): string {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return 'dx-icon-doc';
      case 'doc':
      case 'docx':
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
      case 'jpg':
      case 'jpeg':
      case 'png':
        return '#198754';
      default:
        return '#6c757d';
    }
  }

  getDocumentTypeIcon(documentType?: string): string {
    switch (documentType?.toLowerCase()) {
      case 'contract':
        return 'dx-icon-doc';
      case 'certificate':
        return 'dx-icon-ribbon';
      case 'handbook':
        return 'dx-icon-book';
      case 'policy':
        return 'dx-icon-shield';
      default:
        return 'dx-icon-folder';
    }
  }

  getDocumentTypeColor(documentType?: string): string {
    switch (documentType?.toLowerCase()) {
      case 'contract':
        return '#0d6efd';
      case 'certificate':
        return '#198754';
      case 'handbook':
        return '#fd7e14';
      case 'policy':
        return '#6f42c1';
      default:
        return '#6c757d';
    }
  }

  formatFileSize(sizeString?: string): string {
    if (!sizeString) return 'Unknown size';
    return sizeString;
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}