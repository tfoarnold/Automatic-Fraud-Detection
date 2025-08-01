from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import CustomUser, Transaction
from .serializers import (
    CustomUserSerializer,
    CustomTokenObtainPairSerializer,
    TransactionSerializer,
    TransactionFraudCheckSerializer
)
from django.utils.translation import gettext_lazy as _

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": CustomUserSerializer(user).data,
            "message": _("Utilisateur créé avec succès")
        }, status=status.HTTP_201_CREATED)

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class TransactionListView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(
            models.Q(origin=user) | models.Q(destination=user)
        ).order_by('-date_enregistrement')

    def perform_create(self, serializer):
        serializer.save(origin=self.request.user)

class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference'

class FraudCheckView(generics.UpdateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionFraudCheckSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'reference'

    def update(self, request, *args, **kwargs):
        transaction = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['is_fraud']:
            transaction.mark_as_fraud(
                reason=serializer.validated_data.get('reason', ''),
                confidence=serializer.validated_data['confidence_score']
            )
        else:
            transaction.result_predicted = Transaction.TransactionResult.LEGIT
            transaction.save()

        return Response(TransactionSerializer(transaction).data)
