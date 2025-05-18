import { CommonModule } from '@angular/common';
import { Component, NgModule, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ValidationCallbackData } from 'devextreme-angular/common';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import notify from 'devextreme/ui/notify';
import { AuthService } from '../../services';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-change-passsword-form',
  templateUrl: './change-password-form.component.html',
  standalone: false
})
export class ChangePasswordFormComponent implements OnInit {
  loading = false;
  formData: any = {};
  token: string = '';

  constructor(
    private authService: AuthService, 
    private router: Router, 
    private route: ActivatedRoute,
    private http: HttpClient
  ) { }

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      this.token = params.get('token') || '';
    });
  }

  async onSubmit(e: Event) {
    e.preventDefault();
    const { oldPassword, newPassword } = this.formData;
    this.loading = true;

    try {
      const response = await this.http.post(`${environment.apiUrl}/auth/reset-password-invite`, {
        token: this.token,
        old_password: oldPassword,
        new_password: newPassword
      }).toPromise();
      
      notify('Password updated successfully', 'success', 2000);
      this.router.navigate(['/login-form']);
    } catch (error: any) {
      notify(error.error?.detail || 'Failed to update password', 'error', 2000);
    } finally {
      this.loading = false;
    }
  }

  confirmPassword = (e: ValidationCallbackData) => {
    return e.value === this.formData.newPassword;
  }
}

@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    DxFormModule,
    DxLoadIndicatorModule
  ],
  declarations: [ ChangePasswordFormComponent ],
  exports: [ ChangePasswordFormComponent ]
})
export class ChangePasswordFormModule { }
