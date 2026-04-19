# Claude Blog Monitor

[claude.com/blog](https://claude.com/blog)에 새 글이 올라오면 Slack으로 알림을 보내는 모니터링 도구.

## 동작 방식

1. GitHub Actions가 매시간 `monitor.py` 실행
2. 블로그 페이지를 스크래핑하여 포스트 목록 추출
3. `data/last_posts.json`에 저장된 이전 상태와 비교
4. 새 글 발견 시 Slack Incoming Webhook으로 알림 전송
5. 상태 파일 업데이트 후 자동 커밋

## 설정

### 1. Slack Webhook 생성

1. [Slack API](https://api.slack.com/apps)에서 앱 생성
2. **Incoming Webhooks** 활성화
3. 알림 받을 채널 선택 후 Webhook URL 복사

### 2. GitHub Secrets 등록

Repository Settings > Secrets and variables > Actions에서:

- `SLACK_WEBHOOK_URL` — Slack Webhook URL

### 3. GitHub Actions 활성화

Actions 탭에서 워크플로우를 활성화하면 매시간 자동 실행됩니다.
수동 실행은 Actions > Monitor Claude Blog > Run workflow.

## 로컬 실행

```bash
pip install -r requirements.txt

# Slack 알림 없이 테스트
python monitor.py

# Slack 알림 포함
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/... python monitor.py
```

## 파일 구조

```
├── monitor.py              # 스크래핑 + Slack 알림 스크립트
├── requirements.txt        # Python 의존성
├── data/
│   └── last_posts.json     # 확인한 포스트 URL 상태
└── .github/
    └── workflows/
        └── monitor.yml     # GitHub Actions 워크플로우 (매시간)
```
