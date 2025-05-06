import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import {HTTP_INTERCEPTORS, HttpClientModule, provideHttpClient} from '@angular/common/http';
import { DxDataGridModule, DxFormModule, DxDateBoxModule, DxCalendarModule, DxChartModule, DxPieChartModule, DxSelectBoxModule, DxLoadIndicatorModule } from 'devextreme-angular';
import { AppComponent } from './app.component';
import { DxHttpModule } from 'devextreme-angular/http';
import { SideNavOuterToolbarModule, SingleCardModule } from './layouts';
import { FooterModule, ResetPasswordFormModule, ChangePasswordFormModule, LoginFormModule } from './shared/components';
import { AuthService, ScreenService, AppInfoService } from './shared/services';
import { UnauthenticatedContentModule } from './unauthenticated-content';
import { AppRoutingModule } from './app-routing.module';
import { LeaveCalendarComponent } from './leave-calendar/leave-calendar.component';
import {DxButtonModule} from 'devextreme-angular/ui/button';
import {UserService} from './shared/services/user.service';
import {LeaveService} from './shared/services/leave.service';
import {DxiSeriesModule} from 'devextreme-angular/ui/nested';
import {DashboardModule} from './pages/dashboard/dashboard.component';
import {AuthInterceptor} from './shared/services/authinceptor.service';

@NgModule({
  declarations: [
    AppComponent,
    LeaveCalendarComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    DxDataGridModule,
    DxDateBoxModule,
    DxCalendarModule,
    DxButtonModule,
    DxFormModule,
    DxChartModule,
    DxPieChartModule,
    DxiSeriesModule,
    DxSelectBoxModule,
    DxHttpModule,
    SideNavOuterToolbarModule,
    SingleCardModule,
    FooterModule,
    ResetPasswordFormModule,
    ChangePasswordFormModule,
    LoginFormModule,
    DashboardModule,
    UnauthenticatedContentModule,
    AppRoutingModule,
    DxLoadIndicatorModule
  ],
  providers: [
    {provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true},
    AuthService,
    ScreenService,
    AppInfoService,
    UserService,
    LeaveService
  ],
  exports: [
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
