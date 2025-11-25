# urls.py
from django.urls import path
from .views import RegisterAPIView, LoginAPIView
from .views import CreateGameModeView,CreateGameRecordsView,UpdateGameModeIQView,user_mode_counts,recent_activity,daily_streak,total_puzzles,overall_accuracy
from .views import (
    iq_evolution,
   last_ten_games_chart,
    monthly_iq_chart,
    mode_distribution_chart,user_achievements,peak_metrics,monthly_performance,user_coins,update_coins,greeting_view, user_level_view, leaderboard_view,overall_score,
    marcconrad_game,get_hint,submit_answer,player_overview,user_credentials,get_profile_photo,logout_view,password_reset_request,password_reset_confirm
)
urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
   
   path('create-game/', CreateGameModeView.as_view(), name='create-game'),
   path('create-gameRecords/', CreateGameRecordsView.as_view(), name='create-gameRecords'),
   path('update-gameMode/<int:pk>/', UpdateGameModeIQView.as_view(), name='update-gameMode'),
   
   path('user-mode-counts/', user_mode_counts, name='user-mode-counts'),
   path('recent-activity/', recent_activity, name='recent-activity'),
   
   path('daily-streak/', daily_streak, name='daily-streak'),
   path('total-puzzles/', total_puzzles, name='total-puzzles'),
   path('overall-accuracy/', overall_accuracy, name='overall-accuracy'),
     # IQ Evolution (last 10 games)
    path('iq-evolution/', iq_evolution, name='iq-evolution'),
    # Daily Streak Consistency for chart
    path('last-ten-games-chart/', last_ten_games_chart, name='last_ten_games_chart'),
    # Average Monthly Performance
    path('monthly-iq-chart/', monthly_iq_chart, name='monthly-iq-chart'),
    # Mode Engagement Distribution
    path('mode-distribution-chart/', mode_distribution_chart, name='mode-distribution-chart'),
    path('user-achievements/', user_achievements, name='user-achievements'),
    path('peak-metrics/', peak_metrics, name='peak-metrics'),
    path('monthly-performance/<int:year>/<int:month>/',monthly_performance, name='monthly-performance'),
    path('user-coins/', user_coins, name='user_coins'),
    
    path('update-coins/', update_coins, name='update_coins'),
    path("greeting/", greeting_view, name="greeting"),
    path("user-level/", user_level_view, name="user-level"),
    path("leaderboard/", leaderboard_view, name="leaderboard"),
    path('overall-score/', overall_score, name='overall-score'),
     
    # 1. Secure Question Fetch and Solution Storage (Used by loadNextQuestion)
    path('marcconrad-game/', marcconrad_game, name='marcconrad_game'),
    
    # 2. Secure Hint Generation (Used by handleHint)
    path('get-hint/', get_hint, name='get_hint'),
    
     # 3. Secure Answer Submission/Checking (NEW)
    path('submit-answer/', submit_answer, name='submit_answer'),
    path('player-overview/', player_overview, name='player-overview'),
    path('user-credentials/', user_credentials, name='user-credentials'),
    path('profile/',get_profile_photo, name='get_profile_photo'),
    
    path('logout/', logout_view, name='logout'),
    path("password-reset/", password_reset_request, name="password-reset"),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
]