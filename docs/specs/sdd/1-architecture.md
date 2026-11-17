## 1. 아키텍처

<!-- [context, composition] 배포 단위, 누가 누구와 통신하는지, 데이터가 어디 있는지. 다이어그램 + 글. -->

```mermaid
flowchart LR
  user[사용자] --> web[웹]
  web --> api[API]
  api --> db[(DB)]
```
