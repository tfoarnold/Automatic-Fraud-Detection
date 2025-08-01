from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    TransactionListView,
    TransactionDetailView,
    FraudCheckView
)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/<str:reference>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/<str:reference>/fraud-check/', FraudCheckView.as_view(), name='fraud-check'),
]