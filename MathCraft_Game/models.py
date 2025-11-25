from django.db import models
from django.contrib.auth.models import User

class GameMode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mode = models.CharField(max_length=50)  # 'easy', 'intermediate', 'hard'
    attempt = models.PositiveIntegerField()  # attempt number for the day
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(auto_now_add=True)  # new field for daily grouping
    iq = models.FloatField(null=True, blank=True, help_text="Overall IQ for this attempt")

    class Meta:
        unique_together = ('user', 'date', 'attempt')  # enforces 1,2,3... per day

    def __str__(self):
        return f"{self.user.username} | {self.mode} | Attempt {self.attempt} | {self.date} | IQ: {self.iq}"


class GameQuestionRecord(models.Model):
    """
    Stores each question's details for a particular attempt.
    """
    game_mode = models.ForeignKey(GameMode, on_delete=models.CASCADE, related_name='questions')
    question_number = models.PositiveIntegerField(null=True, blank=True)  # optional for saving incomplete data
    time = models.PositiveIntegerField(null=True, blank=True, help_text="Time in seconds for this question")
    streak = models.PositiveIntegerField(default=0)  # usually 0 by default, no need for null
    user_answer = models.CharField(max_length=255, blank=True)  # blank allows empty string
    correct_answer = models.CharField(max_length=255, blank=True)
    status = models.CharField(
    max_length=20, 
    choices=[
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
        ('skipped', 'Skipped'),
    ],
    blank=True  # optional if status not yet set
) 

    class Meta:
        unique_together = ('game_mode', 'question_number')  
        ordering = ['question_number']

    def __str__(self):
        return f"{self.game_mode.user.username} | Q{self.question_number} | {self.status}"
    

from django.utils.timezone import now

class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_date = models.DateField(default=now)

    class Meta:
        unique_together = ('user', 'login_date')  # one record per user per day
        ordering = ['-login_date']

    def __str__(self):
        return f"{self.user.username} | {self.login_date}"
    


from django.db.models.signals import post_save
from django.dispatch import receiver

# New Update oct 26 
class UserProfile(models.Model):
    """
    Extends the default Django User with game-specific fields like coins.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    coins = models.PositiveIntegerField(default=5000)  # Default 5000 coins on first login
    total_earned = models.PositiveIntegerField(default=0)
    total_spent = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)  # <-- new field
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    def add_coins(self, amount):
        """Safely add coins."""
        self.coins += amount
        self.total_earned += amount
        self.save()

    def spend_coins(self, amount):
        """Safely deduct coins (with check)."""
        if amount <= self.coins:
            self.coins -= amount
            self.total_spent += amount
            self.save()
            return True
        return False


# ✅ Automatically create or update profile for each new user
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)  # creates with default 5000 coins
    else:
        instance.profile.save()
        
        
        
from django.db.models import Count, Q

class UserLevel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='level')
    level = models.PositiveIntegerField(default=0)
    max_level = 100  # optional hard cap

    def __str__(self):
        return f"{self.user.username} | Level {self.level}"

    def update_level(self):
        """
        Only count GameMode attempts with >=5 correct answers.
        Level increases by 1 for every 5 qualifying attempts.
        """
        qualifying_attempts = GameMode.objects.annotate(
            correct_count=Count('questions', filter=Q(questions__status='correct'))
        ).filter(user=self.user, correct_count__gte=5).count()

        self.level = min(qualifying_attempts // 5, self.max_level)
        self.save()

class AchievementReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge_name = models.CharField(max_length=100)
    rewarded = models.BooleanField(default=False)
    rewarded_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge_name')
