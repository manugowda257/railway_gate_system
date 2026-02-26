
from django.contrib import admin
from django.urls import path
from gates.views import home, find_nearest_gate, operator_login, dashboard, operator_logout,add_gate,request_taluk_change,request_new_taluk,live_map,activity_logs
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('nearest/', find_nearest_gate, name='nearest'),
    path('login/', operator_login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', operator_logout, name='logout'),
    path('add-gate/', add_gate, name='add_gate'),
    path('change-taluk/', request_taluk_change, name='change_taluk'),
    path('request-taluk/', request_new_taluk, name='request_taluk'),
    path('map/', live_map, name='live_map'),
    path('logs/', activity_logs, name='activity_logs'),

]


