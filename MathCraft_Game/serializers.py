from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Registration serializer
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password']

    def validate(self, data):
        username = data['username']
        email = data['email']

        # Check if passwords match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})

        # Check if a user exists with BOTH same username AND email
        if User.objects.filter(username=username, email=email).exists():
            raise serializers.ValidationError("User with this username and email already exists.")

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user

# Login serializer
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        data['user'] = user
        return data


from rest_framework import serializers
from .models import GameMode

class GameModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameMode
        fields = ['id', 'user', 'mode', 'attempt', 'created_at', 'date', 'iq']  # add iq here
        read_only_fields = ['id', 'created_at', 'user', 'date']



from .models import GameQuestionRecord

class GameQuestionRecordSerializer(serializers.ModelSerializer):
    # Optional: show user and game_mode info in read-only fields
    user = serializers.CharField(source='game_mode.user.username', read_only=True)
    mode = serializers.CharField(source='game_mode.mode', read_only=True)
    attempt = serializers.IntegerField(source='game_mode.attempt', read_only=True)
    date = serializers.DateField(source='game_mode.date', read_only=True)
    iq = serializers.FloatField(source='game_mode.iq', read_only=True)

    class Meta:
        model = GameQuestionRecord
        fields = [
            'id',
            'game_mode',        
            'user',             
            'mode',             
            'attempt',          
            'date',             
            'question_number',
            'time',
            'streak',
            'user_answer',
            'correct_answer',
            'status',
            'iq',
        ]
        extra_kwargs = {
            'game_mode': {'required': True},
            'question_number': {'required': False, 'allow_null': True}, 
        }
     
     
# New Update oct 26       
from .models import UserProfile
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')  # not read_only
    email = serializers.EmailField(source='user.email')       # not read_only
    photo = serializers.ImageField(allow_null=True, required=False)  # new field

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'photo', 'coins', 'total_earned', 'total_spent', 'created_at']

    def update(self, instance, validated_data):
        # Update related User fields
        user_data = validated_data.pop('user', {})
        if 'username' in user_data:
            instance.user.username = user_data['username']
        if 'email' in user_data:
            instance.user.email = user_data['email']
        instance.user.save()

        # Handle photo explicitly (important for file uploads!)
        photo = validated_data.pop('photo', None)
        if photo is not None:
            instance.photo = photo
        
        # Update remaining profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance



from .models import UserLevel
   
class GreetingSerializer(serializers.Serializer):
    message = serializers.CharField()

class UserLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLevel
        fields = ['level']

class LeaderboardSerializer(serializers.Serializer):
    mode = serializers.CharField()
    username = serializers.CharField()
    iq = serializers.FloatField()
    

