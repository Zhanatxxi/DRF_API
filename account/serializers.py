from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=6, required=True)
    password_confirm = serializers.CharField(min_length=6, required=True)

    class Meta:
        model = User
        fields = (
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name'
        )

    def validate_email(self, email):
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('this user is login')
        return email

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm')
        if password != password_confirm:
            raise serializers.ValidationError('passwords not !=')
        return attrs

    def create(self, validated_data):
        user = User.objects.create(**validated_data)
        user.create_activation_code()
        User.send_activation_mail(user.email, user.activation_code)
        return user


class LoginSerialiser(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password, request=self.context.get('request'))
            if not user:
                raise serializers.ValidationError('wrong enter email and password')
        else:
            raise serializers.ValidationError('Email and Password they required')
        attrs['user'] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError()
        return email

    def send_reset_email(self):
        email = self.validated_data.get('email')
        user = User.objects.get(email=email)
        user.create_activation_code()
        message = f'Code for reset password {user.activation_code}'
        send_mail(
            'Reset password',
            message,
            'test@gmail.com',
            [email, ]
        )


class CreateNewPasswordSerializer(serializers.Serializer):
    activation_code = serializers.CharField(required=True)
    password = serializers.CharField(min_length=6, required=True)
    password_confirm = serializers.CharField(max_length=6, required=True)

    def validate_activation_code(self, code):
        if not User.objects.filter(activation_code=code).exists():
            raise serializers.ValidationError("don't right code")
        return code

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        if password != password_confirm:
            raise serializers.ValidationError('passwords do not совпадают')
        return attrs

    def create_pass(self):
        code = self.validated_data.get('activation_code')
        password = self.validated_data.get('password')
        user = User.objects.get(activation_code=code)
        user.set_password(password)
        user.save()


class ChangePasswordSerializer(serializers.Serializer):
    old_pass = serializers.CharField(required=True)
    new_pass = serializers.CharField(required=True, min_length=6)
    new_pass_confirm = serializers.CharField(required=True, min_length=6)

    def validate_old_pass(self, password):
        request = self.context.get('request')
        if not request.user.check_password(password):
            raise serializers.ValidationError('enter do not right password')
        return password

    def validate(self, attrs):
        pass_ = self.validated_data.get('new_pass')
        pass_confirm = self.validated_data.get('new_pass_confirm')
        if pass_ != pass_confirm:
            raise serializers.ValidationError('неверное подтверждение нового пародля')
        return attrs

    def set_new_password(self):
        request = self.context.get('request')
        new_pass = self.validated_data.get('new_pass')
        user = request.user
        user.set_password(new_pass)
        user.save()


class ActivationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    activation_code = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        activation_code = attrs.get('activation_code')
        if not User.objects.filter(email=email, activation_code=activation_code).exists():
            raise serializers.ValidationError('user not found')
        return attrs

    def activate(self):
        data = self.validated_data
        user = User.objects.get(**data)
        user.is_active = True
        user.activation_code = ''
        user.save()