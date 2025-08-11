from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class Role(models.Model):
    """Modèle pour les rôles utilisateurs"""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    """Manager personnalisé pour le modèle CustomUser"""

    def create_user(self, phone, name, password=None, **extra_fields):
        """Créer un utilisateur normal"""
        if not phone:
            raise ValueError("Le numero de telephone est obligatoire")
        if not name:
            raise ValueError(_("Le nom est obligatoire"))
        user = self.model(
            phone=phone,
            name=name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, name, password=None, **extra_fields):
        """Créer un superutilisateur"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        # Création d'un rôle admin si nécessaire
        admin_role, created = Role.objects.get_or_create(name='Admin')

        extra_fields.setdefault('role', admin_role)

        return self.create_user(
            phone=phone,
            name=name,
            password=password,
            **extra_fields
        )


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Modèle utilisateur personnalisé avec téléphone comme identifiant principal"""

    name = models.CharField(_('Nom complet'), max_length=50)
    phone = models.CharField(_('Téléphone'), max_length=15, unique=True)
    password = models.CharField(max_length=128)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    solde = models.DecimalField(_('Solde'),max_digits=15,decimal_places=2,default=0.00)
    is_active = models.BooleanField(_('Actif'), default=True)
    is_staff = models.BooleanField(_('Staff'), default=False)  # Permet l'accès à l'admin
    date_joined = models.DateTimeField(_('Date inscription'), auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone'  # Définit le téléphone comme identifiant principal
    REQUIRED_FIELDS = ['name']  # Champs obligatoires pour createsuperuser

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split()[0] if self.name else self.phone


class Transaction(models.Model):
    """Modèle pour le suivi des transactions financières avec détection de fraude"""
    
    class TransactionType(models.TextChoices):
        CASH_IN = 'CASH_IN', _('Dépôt')
        CASH_OUT = 'CASH_OUT', _('Retrait')
        TRANSFER = 'TRANSFER', _('Transfert')
        PAYMENT = 'PAYMENT', _('Paiement')
        DEBIT = 'DEBIT', _('Prélèvement')

    class TransactionResult(models.TextChoices):
        FRAUD = 'FRAUD', _('Fraude')
        LEGIT = 'LEGIT', _('Légitime')
        SUSPICIOUS = 'SUSPICIOUS', _('Suspect')
        PENDING = 'PENDING', _('En attente')

    # Référence et type
    reference = models.CharField(
        _('Référence'),
        max_length=20,
        unique=True,
        help_text=_('Identifiant unique de la transaction')
    )
    type = models.CharField(
        _('Type'),
        max_length=10,
        choices=TransactionType.choices,
        default=TransactionType.CASH_OUT
    )
    
    # Horodatage
    step = models.PositiveSmallIntegerField(
        _('Heure'),
        help_text=_('Heure de la transaction (en heures)')
    )
    date_enregistrement = models.DateTimeField(
        _('Date enregistrement'),
        auto_now_add=True
    )
    
    # Parties impliquées
    origin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transactions_envoyees',
        verbose_name=_('Compte origine')
    )
    destination = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transactions_recues',
        null=True,
        blank=True,
        verbose_name=_('Compte destination')
    )
    
    # Montants et soldes
    amount = models.DecimalField(
        _('Montant'),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    oldbalanceOrg = models.DecimalField(
        _('Solde initial origine'),
        max_digits=15,
        decimal_places=2
    )
    newbalanceOrig = models.DecimalField(
        _('Nouveau solde origine'),
        max_digits=15,
        decimal_places=2
    )
    oldbalanceDest = models.DecimalField(
        _('Solde initial destination'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    newbalanceDest = models.DecimalField(
        _('Nouveau solde destination'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Détection de fraude
    result_predicted = models.CharField(
        _('Résultat prédit'),
        max_length=10,
        choices=TransactionResult.choices,
        default=TransactionResult.PENDING
    )
    confidence_score = models.FloatField(
        _('Score de confiance'),
        null=True,
        blank=True,
        help_text=_('Probabilité de fraude (0-1)')
    )
    
    # Métadonnées
    is_verified = models.BooleanField(
        _('Vérifiée'),
        default=False,
        help_text=_('Transaction validée par un agent')
    )
    fraud_flag_reason = models.TextField(
        _('Raison du flag'),
        blank=True,
        help_text=_('Explication du marquage comme fraude')
    )

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-date_enregistrement']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['type']),
            models.Index(fields=['result_predicted']),
            models.Index(fields=['origin', 'date_enregistrement']),
        ]

    def __str__(self):
        return f"{self.reference} - {self.get_type_display()} - {self.amount}"

    def save(self, *args, **kwargs):
        """Génère une référence unique si nouvelle transaction"""
        if not self.reference:
            self.reference = self._generate_reference()
        
        # Calcul automatique des soldes si nécessaire
        if not self.pk:  # Nouvelle transaction
            self.oldbalanceOrg = self.origin.solde
            if self.type in ['CASH_OUT', 'TRANSFER', 'PAYMENT', 'DEBIT']:
                self.newbalanceOrig = self.origin.solde - self.amount
            else:  # CASH_IN
                self.newbalanceOrig = self.origin.solde + self.amount
            
            if self.destination and self.type == 'TRANSFER':
                self.oldbalanceDest = self.destination.solde
                self.newbalanceDest = self.destination.solde + self.amount
        
        super().save(*args, **kwargs)
        
        # Mise à jour des soldes utilisateurs après sauvegarde
        self._update_balances()

    def _generate_reference(self):
        """Génère une référence unique TRX-YYYYMMDD-XXXXXX"""
        from django.utils.crypto import get_random_string
        return f"TRX-{timezone.now().strftime('%Y%m%d')}-{get_random_string(6).upper()}"

    def _update_balances(self):
        """Met à jour les soldes des comptes concernés"""
        if self.type in ['CASH_OUT', 'TRANSFER', 'PAYMENT', 'DEBIT']:
            self.origin.solde = self.newbalanceOrig
            self.origin.save()
        
        if self.type == 'TRANSFER' and self.destination:
            self.destination.solde = self.newbalanceDest
            self.destination.save()

    def mark_as_fraud(self, reason="", confidence=None):
        """Marque explicitement une transaction comme frauduleuse"""
        self.result_predicted = self.TransactionResult.FRAUD
        self.fraud_flag_reason = reason
        self.confidence_score = confidence
        self.save()

    @property
    def is_fraud(self):
        """Property pour vérifier facilement si frauduleuse"""
        return self.result_predicted == self.TransactionResult.FRAUD

    @property
    def duration_minutes(self):
        """Convertit le step (heures) en minutes depuis minuit"""
        return self.step * 60