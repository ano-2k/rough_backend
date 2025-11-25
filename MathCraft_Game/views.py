from django.shortcuts import render

# Create your views here.
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer,UserProfileSerializer

# Registration API
class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # Anyone can register

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "message": "User registered successfully"
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.utils.timezone import now
from .models import LoginHistory  # make sure this import is correct

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # ✅ Create DRF token
            token, created = Token.objects.get_or_create(user=user)

            # ✅ Record today's login for daily streak
            LoginHistory.objects.get_or_create(user=user, login_date=now().date())

            return Response({
                "token": token.key,
                "message": "Login successful"
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from rest_framework import generics, permissions
from django.utils import timezone
from .models import GameMode
from .serializers import GameModeSerializer

class CreateGameModeView(generics.CreateAPIView):
    serializer_class = GameModeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        today = timezone.now().date()
        user = self.request.user

        # Count existing attempts for today for this user using 'date' field
        attempts_today = GameMode.objects.filter(
            user=user,
            date=today
        ).count()

        serializer.save(
            user=user,
            attempt=attempts_today + 1,
            date=today  # explicitly set the date field
        )

from rest_framework.response import Response
from rest_framework import status
from .models import GameQuestionRecord
from .serializers import GameQuestionRecordSerializer

class CreateGameRecordsView(generics.GenericAPIView):
    serializer_class = GameQuestionRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        records = request.data  # Expecting a list of records
        if not isinstance(records, list):
            return Response({"error": "Expected a list of records"}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: ensure user can only post records for their own game_mode
        for r in records:
            if 'game_mode' not in r:
                return Response({"error": "game_mode is required for each record"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=records, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()  # will assign all records properly

        return Response({"status": "success", "saved": len(records)}, status=status.HTTP_201_CREATED)
    
    
    
class UpdateGameModeIQView(generics.UpdateAPIView):
    queryset = GameMode.objects.all()
    serializer_class = GameModeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        game_mode = self.get_object()

        # Only allow the owner to update
        if game_mode.user != request.user:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        iq = request.data.get("iq")
        if iq is None:
            return Response({"detail": "IQ value is required."}, status=status.HTTP_400_BAD_REQUEST)

        game_mode.iq = iq
        game_mode.save()
        serializer = self.get_serializer(game_mode)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_mode_counts(request):
    """
    Returns total counts of each mode (Easy, Intermediate, Hard)
    for the currently logged-in user.
    """
    user = request.user

    easy_count = GameMode.objects.filter(user=user, mode__iexact='easy').count()
    intermediate_count = GameMode.objects.filter(user=user, mode__iexact='intermediate').count()
    hard_count = GameMode.objects.filter(user=user, mode__iexact='hard').count()

    total = easy_count + intermediate_count + hard_count

    data = {
        "Easy": easy_count,
        "Intermediate": intermediate_count,
        "Hard": hard_count,
        "Total": total,
    }

    return Response(data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activity(request):
    """
    Returns the recent game attempts (GameMode) for the logged-in user.
    Each record shows: Time, Mode, Total Streak, IQ.
    """
    user = request.user

    # Fetch the latest GameModes for this user (e.g., last 10)
    recent_games = GameMode.objects.filter(user=user).order_by('-created_at')[:10]

    data = []
    for game in recent_games:
        # Aggregate total streak or maximum streak for this attempt
        total_streak = game.questions.aggregate(total=Sum('streak'))['total'] or 0

        data.append({
            "datetime": localtime(game.created_at).strftime("%Y-%m-%d %H:%M"),
            "mode": game.mode.capitalize(),  # normalize mode
            "total_streak": total_streak,   # sum of all question streaks
            "iq": game.iq or 0,
        })

    return Response(data, status=status.HTTP_200_OK)


from django.utils.timezone import localtime, now
from datetime import timedelta
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_streak(request):
    user = request.user
    today = localtime(now()).date()

    # ✅ Record today's login if not already saved
    LoginHistory.objects.get_or_create(user=user, login_date=today)

    # ✅ Get all login dates (latest first)
    login_dates = list(
        LoginHistory.objects.filter(user=user)
        .order_by('-login_date')
        .values_list('login_date', flat=True)
    )

    if not login_dates:
        return Response({"daily_streak": 1})  # shouldn't happen since we just added one

    # ✅ Initialize streak
    streak = 1

    # ✅ Loop through consecutive dates
    for i in range(1, len(login_dates)):
        prev = login_dates[i - 1]
        curr = login_dates[i]

        if (prev - curr).days == 1:
            streak += 1
        else:
            break  # stop counting if there's a gap

    return Response({"daily_streak": streak})


# --- Total Puzzles Attempted API ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def total_puzzles(request):
    user = request.user
    # Total GameMode instances = total puzzles attempted by user
    total_attempts = GameMode.objects.filter(user=user).count()
    return Response({"total_puzzles_attempted": total_attempts})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overall_accuracy(request):
    user = request.user

    # All question records for this user's puzzles
    records = GameQuestionRecord.objects.filter(game_mode__user=user)
    total_questions = records.count()  # total questions attempted
    correct_questions = records.filter(status='correct').count()  # total correct answers

    accuracy = (correct_questions / total_questions * 100) if total_questions else 0
    return Response({"overall_accuracy": round(accuracy, 2)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def iq_evolution(request):
    """
    Returns the last 10 IQ scores for the logged-in user.
    """
    user = request.user
    last_games = GameMode.objects.filter(user=user).order_by('-created_at')[:10]
    last_games = list(reversed(last_games))  # oldest → newest

    data = {
        "labels": [f"Game {i+1}" for i in range(len(last_games))],
        "iq_scores": [g.iq or 0 for g in last_games],
    }
    return Response(data)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def last_ten_games_chart(request):
    user = request.user

    # Get the last 10 games, newest first
    last_games = GameMode.objects.filter(user=user).order_by('-created_at')[:10]

    # Reverse to oldest → newest for chart display
    last_games = list(reversed(last_games))

    labels = [f"Game {i+1}" for i in range(len(last_games))]
    total_streaks = []
    modes = []

    for game in last_games:
        questions = game.questions.all()
        total_streak = sum(q.streak for q in questions)
        total_streaks.append(total_streak)
        modes.append(game.mode.capitalize())

    return Response({
        "labels": labels,
        "total_streaks": total_streaks,
        "modes": modes
    })
    
    
from django.db.models import Avg
from django.db.models.functions import TruncMonth

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_iq_chart(request):
    """
    Returns average IQ per month for the last 6 months for the user.
    """
    user = request.user
    qs = (
        GameMode.objects.filter(user=user)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(avg_iq=Avg('iq'))
        .order_by('month')
    )

    labels = [q['month'].strftime("%b") for q in qs]
    avg_iq = [round(q['avg_iq'], 2) for q in qs]

    return Response({"labels": labels, "avg_iq": avg_iq})


##### above added in real repo 

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mode_distribution_chart(request):
    """
    Returns count of games played per mode for the logged-in user.
    """
    user = request.user
    easy = GameMode.objects.filter(user=user, mode__iexact='easy').count()
    intermediate = GameMode.objects.filter(user=user, mode__iexact='intermediate').count()
    hard = GameMode.objects.filter(user=user, mode__iexact='hard').count()

    return Response({
        "labels": ["Easy", "Intermediate", "Hard"],
        "counts": [easy, intermediate, hard]
    })


from django.db.models import Max, Sum
from django.utils.timezone import now
from .models import LoginHistory,AchievementReward

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_achievements(request):
    user = request.user
    profile = user.profile  # Use the related_name from UserProfile

    # ------------------------
    # 1. Code Crusader: total correct answers
    # ------------------------
    total_correct = GameQuestionRecord.objects.filter(
        game_mode__user=user, status='correct'
    ).count()

    # ------------------------
    # 2. Master Calibrator: Best IQ
    # ------------------------
    best_iq = GameMode.objects.filter(user=user).aggregate(max_iq=Max('iq'))['max_iq'] or 0

    # ------------------------
    # 3. Daily Devotion: Login-based streak
    # ------------------------
    today = localtime(now()).date()
    login_dates_qs = LoginHistory.objects.filter(user=user).order_by('-login_date').values_list('login_date', flat=True)
    login_dates = list(login_dates_qs)

    streak = 0
    if login_dates:
        prev_date = None
        for d in login_dates:
            if prev_date is None:
                streak = 1 if d == today else 0
                prev_date = d
            else:
                if (prev_date - d).days == 1:
                    streak += 1
                    prev_date = d
                else:
                    break
        if today not in login_dates:
            streak += 1
    else:
        streak = 1

    # ------------------------
    # 4. Lightning / Speed Badge: Best hard mode streak
    # ------------------------
    hard_mode_games = GameMode.objects.filter(user=user, mode__iexact='hard')
    hard_best_streak = 0
    lightning_unlocked = False

    for g in hard_mode_games:
        total_streak = g.questions.aggregate(total=Sum('streak'))['total'] or 0
        if total_streak > hard_best_streak:
            hard_best_streak = total_streak
        if total_streak == 50:
            lightning_unlocked = True

    # ------------------------
    # 5. Apex Challenger: Hard games with 5+ correct answers
    # ------------------------
    apex_count = 0
    for g in hard_mode_games:
        correct_count = g.questions.filter(status='correct').count()
        if correct_count >= 5:
            apex_count += 1

    # ------------------------
    # 6. True Polymath: Games per mode
    # ------------------------
    easy_count = GameMode.objects.filter(user=user, mode__iexact='easy').count()
    intermediate_count = GameMode.objects.filter(user=user, mode__iexact='intermediate').count()
    hard_count = hard_mode_games.count()

    # ------------------------
    # 7. Total games
    # ------------------------
    total_games = easy_count + intermediate_count + hard_count

    # ------------------------
    # 8. Coin reward for unlocked badges
    # ------------------------
    achievements = {
        "code_crusader": total_correct >= 100,
        "master_calibrator": best_iq >= 100,
        "daily_devotion": streak >= 30,
        "lightning_solver": lightning_unlocked,
        "apex_challenger": apex_count >= 50,
        "true_polymath": easy_count >= 5 and intermediate_count >= 5 and hard_count >= 5,
    }

    rewarded_badges = []

    for badge_name, unlocked in achievements.items():
        if unlocked:
            # Only reward if not already rewarded
            if not AchievementReward.objects.filter(user=user, badge_name=badge_name, rewarded=True).exists():
                profile.add_coins(5000)  # Add 5000 coins
                AchievementReward.objects.create(user=user, badge_name=badge_name, rewarded=True)
                rewarded_badges.append(badge_name)

    # ------------------------
    # Response
    # ------------------------
    return Response({
        "code_crusader": {
            "current": total_correct,
            "target": 100,
            "status": "UNLOCKED" if achievements["code_crusader"] else "LOCKED"
        },
        "master_calibrator": {
            "best_iq": best_iq,
            "status": "UNLOCKED" if achievements["master_calibrator"] else "LOCKED"
        },
        "daily_devotion": {
            "current_streak": streak,
            "target": 30,
            "status": "UNLOCKED" if achievements["daily_devotion"] else "LOCKED"
        },
        "speed_badge": {
            "best_streak": hard_best_streak,
            "max_streak": 50,
            "status": "UNLOCKED" if achievements["lightning_solver"] else "LOCKED"
        },
        "apex_challenger": {
            "current": apex_count,
            "target": 50,
            "status": "UNLOCKED" if achievements["apex_challenger"] else "LOCKED"
        },
        "true_polymath": {
            "Easy": easy_count,
            "Intermediate": intermediate_count,
            "Hard": hard_count,
            "status": "UNLOCKED" if achievements["true_polymath"] else "LOCKED"
        },
        "total_games": total_games,
        "rewarded_badges": rewarded_badges,
        "coins": profile.coins
    })

    
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, F, FloatField
from django.db.models.functions import Coalesce
from .models import GameMode, GameQuestionRecord

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peak_metrics(request):
    user = request.user

    # 1. Longest Combo Streak per mode
    longest_streak_data = {}
    for mode in ['easy', 'intermediate', 'hard']:
        attempts = GameMode.objects.filter(user=user, mode__iexact=mode).annotate(
            total_streak=Coalesce(Sum('questions__streak'), 0)
        )
        # Get max streak for this mode
        max_streak = attempts.aggregate(max_streak=Coalesce(Max('total_streak'), 0))['max_streak']
        longest_streak_data[mode.title()] = max_streak

    # 2. Fastest Puzzle Time (integer only)
    fastest_time = {}
    for mode in ['easy', 'intermediate', 'hard']:
        attempts = GameMode.objects.filter(user=user, mode__iexact=mode).annotate(
            total_time=Coalesce(Sum('questions__time'), 0)
        ).order_by('total_time')  # smallest first

        if attempts.exists():
            # Convert to int to remove floating points
            fastest_time[mode.title()] = f"{int(attempts.first().total_time)}s"
        else:
            fastest_time[mode.title()] = "0s"

    # 3. Highest Mode Accuracy (integer only)
    accuracy = {}
    for mode in ['easy', 'intermediate', 'hard']:
        questions = GameQuestionRecord.objects.filter(game_mode__user=user, game_mode__mode__iexact=mode)
        total_q = questions.count()
        correct_q = questions.filter(status='correct').count()
        acc_percent = (correct_q / total_q * 100) if total_q > 0 else 0
        # Convert to int for no decimal
        accuracy[mode.title()] = f"{int(acc_percent)}%"

    return Response({
        "longestStreak": longest_streak_data,
        "fastestPuzzle": fastest_time,
        "highestModeMastery": accuracy
    })

    
from .models import UserProfile

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_coins(request):
    """
    Returns the coin balance of the logged-in user.
    """
    profile = UserProfile.objects.get(user=request.user)
    
    data = {
        "username": request.user.username,
        "coins": profile.coins,
        "total_earned": profile.total_earned,
        "total_spent": profile.total_spent,
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_coins(request):
    """
    Updates the user's coins.
    Request body:
        {
            "amount": 100,    # positive or negative
            "action": "add"   # or "spend"
        }
    """
    user = request.user
    profile = UserProfile.objects.get(user=user)

    amount = request.data.get('amount')
    action = request.data.get('action')

    if amount is None or action not in ['add', 'spend']:
        return Response({"error": "Invalid parameters"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        amount = int(amount)
    except ValueError:
        return Response({"error": "Amount must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    
    if action == 'add':
        profile.add_coins(amount)
        return Response({
            "message": f"{amount} coins added",
            "coins": profile.coins,
            "total_earned": profile.total_earned
        })
    elif action == 'spend':
        success = profile.spend_coins(amount)
        if success:
            return Response({
                "message": f"{amount} coins spent",
                "coins": profile.coins,
                "total_spent": profile.total_spent
            })
        else:
            return Response({"error": "Insufficient coins"}, status=status.HTTP_400_BAD_REQUEST)
    
    
from datetime import datetime  
  
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_performance(request, year, month):
    user = request.user
    try:
        year, month = int(year), int(month)
    except ValueError:
        return Response({"error": "Invalid year or month"}, status=400)

    # Month range (timezone-aware)
    try:
        start_date = timezone.make_aware(datetime(year, month, 1))
        if month == 12:
            end_date = timezone.make_aware(datetime(year + 1, 1, 1))
        else:
            end_date = timezone.make_aware(datetime(year, month + 1, 1))
    except Exception:
        return Response({"error": "Invalid date"}, status=400)

    # Fetch games for this month
    games = GameMode.objects.filter(user=user, created_at__gte=start_date, created_at__lt=end_date)
    total_puzzles = games.count()

    # Mode breakdown
    mode_map = {"easy": "Easy", "intermediate": "Intermediate", "hard": "Hard"}
    mode_counts = {v: 0 for v in mode_map.values()}

    for m in games.values('mode').annotate(count=Count('id')):
        normalized_mode = mode_map.get(m['mode'].lower(), m['mode'].capitalize())
        mode_counts[normalized_mode] += m['count']

    # IQ summary (sum of per-attempt IQs per mode)
    iq_summary = {}
    for mode in ['easy', 'intermediate', 'hard']:
        total_iq = (
            GameMode.objects.filter(
                user=user,
                mode__iexact=mode,
                created_at__gte=start_date,
                created_at__lt=end_date
            )
            .exclude(iq__isnull=True)
            .aggregate(total_iq=Sum('iq'))['total_iq'] or 0
        )
        iq_summary[mode_map[mode]] = int(total_iq)  # remove decimals, integer only

    # Coins stats
    try:
        profile = UserProfile.objects.get(user=user)
        coins_earned = profile.total_earned or 0
        coins_spent = profile.total_spent or 0
    except UserProfile.DoesNotExist:
        coins_earned = 0
        coins_spent = 0

    data = {
        "total_puzzles": total_puzzles,
        "total_coins_earned": coins_earned,
        "total_coins_spent": coins_spent,
        "iqSummary": iq_summary,
        "mode_counts": mode_counts,
    }

    return Response(data, status=200)


from django.utils.timezone import localtime

# Greeting API
@api_view(['GET'])
def greeting_view(request):
    user = request.user
    current_hour = localtime().hour  # now uses Asia/Colombo timezone

    if 5 <= current_hour < 12:
        greet = "Good Morning"
    elif 12 <= current_hour < 17:
        greet = "Good Afternoon"
    elif 17 <= current_hour < 21:
        greet = "Good Evening"
    else:
        greet = "Good Night"

    return Response({"greet": greet, "username": user.username})


from django.db.models import Q
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_level_view(request):
    user = request.user

    # Count qualifying attempts (>=5 correct answers)
    qualifying_attempts = GameMode.objects.annotate(
        correct_count=Count('questions', filter=Q(questions__status='correct'))
    ).filter(user=user, correct_count__gte=5).count()

    # Level increases by 1 for every 5 qualifying attempts
    level = min((qualifying_attempts // 5) + 1, 100)

    # Progress toward next level (leftover attempts)
    progress_count = qualifying_attempts % 5
    max_count = 5  # Number of qualifying attempts needed to level up

    return Response({
        "level": level,
        "progress_count": progress_count,
        "max_count": max_count
    })

@api_view(['GET'])
def leaderboard_view(request):
    """
    Returns the top 5 users per mode based on overall IQ in that mode.
    Each user's IQ is summed over all their attempts in that mode (like overall_score API).
    """
    modes = ['easy', 'intermediate', 'hard']
    data = {}

    for mode in modes:
        # 1. Get total IQ per user for this mode (sum of IQs per attempt)
        user_scores_qs = (
            GameMode.objects
            .filter(mode__iexact=mode)
            .values('user__username')
            .annotate(total_iq=Sum('iq'))  # sum of all attempts
            .order_by('-total_iq')  # highest first
        )

        top_users = user_scores_qs[:5]

        data[mode] = [
            {
                "username": u['user__username'],
                "overall_score": int(u['total_iq'] or 0)
            } for u in top_users
        ]

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overall_score(request):
    user = request.user
    
    # Sum IQ from all attempts and convert to integer
    total_score = int(GameMode.objects.filter(user=user).aggregate(total=Sum('iq'))['total'] or 0)

    # Breakdown per mode
    breakdown_qs = GameMode.objects.filter(user=user).values('mode').annotate(mode_score=Sum('iq'))
    breakdown = [{b['mode']: int(b['mode_score'])} for b in breakdown_qs]

    return Response({
        "user": user.username,
        "overall_score": total_score,
        "breakdown": breakdown
    })
    
    
    
import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
# IMPORTANT: Ensure your model imports are correct:
from .models import GameQuestionRecord, GameMode 
from .utils.hints import generate_hint 

@api_view(['POST']) 
@permission_classes([IsAuthenticated]) 
def marcconrad_game(request):
    """
    1. Fetches the question and correct answer from the external API.
    2. SECURELY saves the correct answer to a GameQuestionRecord.
    3. Returns ONLY the question image to the frontend.
    """
    game_mode_id = request.data.get('game_mode_id')
    question_number = request.data.get('question_number')

    if not all([game_mode_id, question_number]):
        return Response({"error": "Missing game context (mode ID or Q number)."}, status=400)
    
    # 1. Retrieve parent GameMode instance (Security check: belongs to the current user)
    try:
        game_mode_instance = get_object_or_404(
            GameMode, 
            id=game_mode_id, 
            user=request.user
        )
    except Exception:
        return Response({"error": "Game Mode not found or does not belong to user."}, status=404)

    try:
        # 2. Fetch from the external API
        external_url = "http://marcconrad.com/uob/banana/api.php?out=json"
        response = requests.get(external_url, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # CRITICAL FIX for KeyError: 0
        if isinstance(data, list) and len(data) > 0:
            question_data = data[0]
        elif isinstance(data, dict):
            question_data = data
        else:
            raise ValueError("External API returned empty or unreadable data structure.")
        
        # Extract data
        fetched_question_img = question_data.get('question') 
        fetched_solution = question_data.get('solution')    

        if not fetched_question_img or fetched_solution is None: # Check for None explicitly
            raise ValueError("External API response was valid JSON but lacked 'question' or 'solution' fields.")

        # 3. Securely store the solution in the database (Create or update the record)
        # We use a transaction to ensure database integrity on creation
        with transaction.atomic():
            record, created = GameQuestionRecord.objects.update_or_create(
                game_mode=game_mode_instance, 
                question_number=question_number,
                defaults={
                    'correct_answer': str(fetched_solution), 
                }
            )

        # 4. Return ONLY the question image (Do NOT return the solution!)
        return Response({
            "question": fetched_question_img, 
        })
        
    except requests.exceptions.Timeout:
        return Response({"error": "External API Timeout. Please try again."}, status=504)
    except requests.exceptions.RequestException as e:
        # Catch all connection/HTTP errors
        return Response({"error": f"External API Fetch Error. Detail: {type(e).__name__}: {str(e)}"}, status=503)
    except (IndexError, TypeError, ValueError, KeyError) as e:
        # Catch errors during JSON parsing or data extraction (including the KeyError: 0 fix)
        return Response({"error": f"External API Data Error. Unexpected response format. Detail: {e}"}, status=500)
    except Exception as e:
        # Final fallback for unexpected internal errors
        return Response({"error": f"An unexpected internal error occurred: {type(e).__name__}: {str(e)}"}, status=500)



# ===================================================================
# 2. SECURE HINT GENERATION API
# ===================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def get_hint(request):
    """
    Retrieves the solution from the database and uses the utility to generate a hint.
    """
    game_mode_id = request.data.get('game_mode_id')
    question_number = request.data.get('question_number')
    rotation_index = request.data.get('rotation_index', 0)

    if not all([game_mode_id, question_number]):
        return Response({"error": "Missing game_mode_id or question_number"}, status=400)

    try:
        # Retrieve the question record to get the correct answer securely
        record = get_object_or_404(
            GameQuestionRecord, 
            game_mode_id=game_mode_id, 
            question_number=question_number
        )
        
        solution = record.correct_answer # This is the secure solution field
        
        # Call the Python hint utility
        hint_text = generate_hint(str(solution), rotation_index)
        
        # Return only the hint text
        return Response({"hint_text": hint_text})

    except GameQuestionRecord.DoesNotExist:
        return Response({"error": "Game question record not found."}, status=404)
    except Exception as e:
        return Response({"error": f"An internal error occurred while generating the hint: {str(e)}"}, status=500)
    
    
from django.db import transaction 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request):
    """
    1. Retrieves the existing GameQuestionRecord to get the correct answer.
    2. Calculates status, streak, and IQ delta.
    3. Updates the GameQuestionRecord with the user's answer and results.
    """
    game_mode_id = request.data.get('game_mode_id')
    question_number = request.data.get('question_number')
    user_answer = request.data.get('user_answer')
    time_taken = request.data.get('time_taken')
    current_streak = request.data.get('streak', 0) # Use 0 as default if missing
    hint_used = request.data.get('hint_used', False)

    if not all([game_mode_id, question_number, user_answer is not None, time_taken is not None]):
        return Response({"error": "Missing required submission data."}, status=400)

    try:
        # 1. Retrieve the existing question record (This is the fix for the initial error)
        # SECURITY: Ensure the record belongs to the current user's game mode
        record = get_object_or_404(
            GameQuestionRecord, 
            game_mode_id=game_mode_id, 
            question_number=question_number,
            game_mode__user=request.user # Essential security check
        )
        
        # 2. Process Answer and Calculate Metrics
        
        # Convert to string for consistent comparison (all values are strings in the model)
        correct_answer_str = record.correct_answer 
        user_answer_str = str(user_answer)
        
        is_correct = (correct_answer_str == user_answer_str)
        
        if user_answer_str == "SKIPPED":
            status = 'skipped'
            final_streak = 0
        elif is_correct:
            status = 'correct'
            final_streak = min(current_streak + 1, 5) # Max streak of 5
        else:
            status = 'incorrect'
            final_streak = 0

        # --- Example IQ/Score Calculation Placeholder ---
        # NOTE: You need to implement your actual scoring/IQ logic here.
        # This is a basic placeholder.
        iq_delta = 0.0 # Placeholder
        if status == 'correct':
             iq_delta = 5.0 # Example gain
        elif status == 'incorrect':
             iq_delta = -3.0 # Example loss
        # Apply penalty for using hint
        if hint_used:
             iq_delta = iq_delta * 0.5


        # 3. Update the GameQuestionRecord with the result (Use a transaction for safety)
        with transaction.atomic():
            record.user_answer = user_answer_str
            record.status = status
            record.time = time_taken
            record.streak = final_streak
            # NOTE: Assuming 'iq' field stores the delta/score for *this* question
            # Your overall IQ calculation likely happens at the end of the game (GameMode update)
            record.iq = iq_delta
            record.save()
        
        # 4. Return the result
        return Response({
            "status": status,
            "correct_answer": correct_answer_str,
            "final_streak": final_streak,
            "iq_delta": iq_delta
        }, status=200)

    except GameQuestionRecord.DoesNotExist:
        # Clear error for the client
        return Response({"error": "Question record not found. Did the question load successfully?"}, status=404)
    except Exception as e:
        # Final fallback
        return Response({"error": f"An internal error occurred: {type(e).__name__}: {str(e)}"}, status=500)


from django.db.models import Sum, Max, IntegerField
from django.db.models.functions import Coalesce
from django.utils.timezone import localtime
from .models import GameMode, GameQuestionRecord, AchievementReward

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_overview(request):
    user = request.user
    profile = user.profile  # from UserProfile (auto-created)
    join_date = localtime(user.date_joined).strftime("%Y-%m-%d")
    
    photo_url = request.build_absolute_uri(profile.photo.url) if profile.photo else None

    # --------------------------
    # 1️⃣ Overall Score
    # --------------------------
    total_score = int(
        GameMode.objects.filter(user=user).aggregate(
            total=Coalesce(Sum('iq'), 0, output_field=IntegerField())
        )['total']
    )

    # --------------------------
    # 2️⃣ Achievements Unlocked (human-readable)
    # --------------------------
    unlocked_achievements = AchievementReward.objects.filter(
        user=user, rewarded=True
    ).values_list('badge_name', flat=True)
    # Convert underscores to spaces & capitalize words
    achievements_readable = [name.replace('_', ' ').title() for name in unlocked_achievements]

    # --------------------------
    # 3️⃣ Overall Accuracy
    # --------------------------
    records = GameQuestionRecord.objects.filter(game_mode__user=user)
    total_questions = records.count()
    correct_questions = records.filter(status='correct').count()
    overall_accuracy = round((correct_questions / total_questions * 100), 2) if total_questions else 0

    # --------------------------
    # 4️⃣ Total Puzzles Solved
    # --------------------------
    total_puzzles = GameMode.objects.filter(user=user).count()

    # --------------------------
    # 5️⃣ Highest Streak Combo per mode
    # --------------------------
    longest_streak_data = {}
    for mode in ['easy', 'intermediate', 'hard']:
        attempts = GameMode.objects.filter(user=user, mode__iexact=mode).annotate(
            total_streak=Coalesce(Sum('questions__streak'), 0, output_field=IntegerField())
        )
        max_streak = attempts.aggregate(
            max_streak=Coalesce(Max('total_streak'), 0, output_field=IntegerField())
        )['max_streak']
        longest_streak_data[mode.title()] = max_streak

    # --------------------------
    # 6️⃣ Final Response
    # --------------------------
    return Response({
        "username": user.username,
        "email": user.email,
        "photo_url": photo_url,
        "join_date": join_date,
        "overall_score": total_score,
        "overall_accuracy": overall_accuracy,
        "total_puzzles_solved": total_puzzles,
        "highest_streak_combo": longest_streak_data,  # per mode
        "achievements_unlocked": achievements_readable,
        "coins": profile.coins,
    })
    
    
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def user_credentials(request):
    profile = request.user.profile

    if request.method == 'GET':
        photo_url = request.build_absolute_uri(profile.photo.url) if profile.photo else None
        return Response({
            "username": request.user.username,
            "email": request.user.email,
            "photo_url": photo_url,
        })

    if request.method == 'PATCH':
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            photo_url = request.build_absolute_uri(serializer.instance.photo.url) if serializer.instance.photo else None
            return Response({
                "message": "Credentials updated successfully",
                "username": serializer.instance.user.username,
                "email": serializer.instance.user.email,
                "photo_url": photo_url,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_photo(request):
    """
    Returns only the profile photo URL of the logged-in user.
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
        photo_url = request.build_absolute_uri(profile.photo.url) if profile.photo else None
        return Response({"photo": photo_url})
    except UserProfile.DoesNotExist:
        return Response({"photo": None})
   
    
from django.core.exceptions import ObjectDoesNotExist
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logs out the authenticated user by deleting their token.
    """
    try:
        # Delete the user's token
        request.user.auth_token.delete()
    except ObjectDoesNotExist:
        # Token might not exist, safe to ignore
        pass

    return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

@api_view(['POST'])
def password_reset_request(request):
    """
    Expects:
    {
        "username": "username_entered",
        "email": "email_entered"
    }
    Sends a professional MathCraft password reset email.
    """
    username = request.data.get("username")
    email = request.data.get("email")

    if not username or not email:
        return Response({"detail": "Username and email required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"detail": "Username does not exist."}, status=status.HTTP_404_NOT_FOUND)

    if user.email != email:
        name, domain = user.email.split("@")
        masked_name = name[0] + "*"*(len(name)-2) + name[-1] if len(name) > 2 else name[0]+"*"
        masked_email = f"{masked_name}@{domain}"
        return Response({"detail": f"Email does not match. Hint: {masked_email}"}, status=status.HTTP_400_BAD_REQUEST)

    # Generate reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

    # Compose professional HTML email
    subject = "MathCraft Quest: Reset Your Password and Reclaim Your Power!"
    message_text = f"Hello {user.username},\n\nWe received a request to reset your MathCraft password.\nClick the link below to reset it:\n{reset_link}\n\nIf you did not request this, please ignore this email.\n\nMathCraft Team"

    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #fdf2f8; color: #333; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            <h2 style="color: #e11d48;">Reset Your Password and Reclaim Your Power!</h2>
            <p>Hello <strong>{user.username}</strong>,</p>
            <p>We received a request to reset your MathCraft account password.</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #ec4899; color: #fff; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
            </p>
            <p>If the button above does not work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{reset_link}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #555; font-size: 14px; line-height: 1;">
    <strong>About MathCraft:</strong><br><br>
    
    MathCraft is a thrilling puzzle game where your goal is to find the number hidden behind the <strong>🍌 (banana) symbol</strong> in each equation.<br><br>
    
    Solve puzzles in three difficulty levels <strong>Easy (90s)</strong>, <strong>Intermediate (60s)</strong>, and <strong>Hard (30s)</strong> and keep your streaks high to earn more rewards.<br><br>
    
    Track your progress on a <strong>personal dashboard</strong>: see your streaks, coins, and achievements, and challenge yourself to improve every day!
</p>

            <p>Thank you,<br><strong>MathCraft Team</strong></p>
        </div>
    </body>
    </html>
    """

    # Send email
    send_mail(
        subject=subject,
        message=message_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
        html_message=html_message
    )

    return Response({"detail": "Password reset email sent successfully. Check your inbox."}, status=status.HTTP_200_OK)


from django.utils.http import urlsafe_base64_decode
@api_view(['POST'])
def password_reset_confirm(request):
    """
    Expects:
    {
        "uid": "<uid_from_email>",
        "token": "<token_from_email>",
        "password": "<new_password>"
    }
    """
    uid = request.data.get("uid")
    token = request.data.get("token")
    new_password = request.data.get("password")

    if not uid or not token or not new_password:
        return Response({"detail": "UID, token, and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        uid = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({"detail": "Invalid UID."}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)