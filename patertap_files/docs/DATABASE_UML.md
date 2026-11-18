# База данных PaterTap

```mermaid
erDiagram
    LISTINGS ||--o{ INQUIRIES : receives
    LISTINGS {
        int id PK
        text title
        text city
        text district
        int price
        int rooms
        text description
    }
    INQUIRIES {
        int id PK
        int listing_id FK
        text name
        text contact
        text message
        text created_at
    }
    ROOMMATES {
        int id PK
        text name
        int budget
        text sleep
        text cleanliness
        text social
        text bio
    }
```

Одно объявление может получить много откликов (связь один-ко-многим через listing_id). Таблица roommates самостоятельная: совместимость считается в коде в /api/matches и в базе не хранится.
