from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('my-books/', views.my_books, name='my_books'),
    path('my-books/add/', views.add_book, name='add_book'),
    path('my-books/<int:pk>/edit/', views.edit_book, name='edit_book'),
    path('my-books/<int:pk>/delete/', views.delete_book, name='delete_book'),
    path('exchange/', views.exchange_catalog, name='exchange'),
    path('exchanges/', views.exchanges_view, name='exchanges'),
    path('exchanges/borrow/<int:pk>/', views.borrow_book, name='borrow_book'),
    path('exchanges/<int:pk>/cancel/', views.cancel_exchange, name='cancel_exchange'),
    path('exchanges/<int:pk>/message/', views.send_exchange_message, name='send_exchange_message'),
    path('exchanges/<int:pk>/handover/', views.confirm_handover, name='confirm_handover'),
    path('exchanges/<int:pk>/return/', views.confirm_return, name='confirm_return'),
    path('exchanges/<int:pk>/<str:action>/', views.respond_exchange, name='respond_exchange'),
]
