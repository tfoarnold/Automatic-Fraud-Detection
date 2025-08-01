from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, Transaction, Role
from django.utils.translation import gettext_lazy as _
import logging



logger = logging.getLogger(__name__)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']

class CustomUserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        write_only=True,
        required=False
    )
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone', 'name','password', 
            'role', 'role_id',
            'is_active', 'date_joined'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            phone=validated_data['phone'],
            name=validated_data['name'],
            password=validated_data.get('password'),
            role=validated_data.get('role')
        )
        return user

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Récupération des credentials
        phone = attrs.get('phone', '')
        password = attrs.get('password', '')
        
        # Trouver l'utilisateur
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active account found")

        # Vérification manuelle du mot de passe
        if not check_password(password, user.password):
            raise serializers.ValidationError("Invalid password")

        # Génération du token si tout est valide
        refresh = self.get_token(user)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': CustomUserSerializer(user).data
        }

class TransactionSerializer(serializers.ModelSerializer):
    origin = CustomUserSerializer(read_only=True)
    origin_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='origin',
        write_only=True
    )
    destination = CustomUserSerializer(read_only=True)
    destination_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='destination',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            'reference', 'type', 'step', 'amount',
            'oldbalanceOrg', 'newbalanceOrig',
            'oldbalanceDest', 'newbalanceDest',
            'result_predicted', 'confidence_score',
            'date_enregistrement', 'is_verified',
            'fraud_flag_reason', 'origin', 'origin_id',
            'destination', 'destination_id'
        ]
        read_only_fields = [
            'reference', 'oldbalanceOrg', 'newbalanceOrig',
            'oldbalanceDest', 'newbalanceDest', 'date_enregistrement'
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Le montant doit être positif"))
        return value

class TransactionFraudCheckSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
    is_fraud = serializers.BooleanField()
    confidence_score = serializers.FloatField(min_value=0, max_value=1)
    reason = serializers.CharField(required=False, allow_blank=True)