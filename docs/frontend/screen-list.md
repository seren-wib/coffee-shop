# 화면 목록 (Screen List)

커피 원두 쇼핑몰 시스템의 프론트엔드 화면 목록이다.  
유스케이스 다이어그램과 요구사항 정의를 기준으로 각 화면의 사용자, 목적, 주요 기능 및 관련 유스케이스를 정리한다.

| 화면 ID | 화면명 | 사용자 | 화면 설명 | 주요 기능 | 관련 유스케이스 |
|---|---|---|---|---|---|
| SCR-01 | 원두 목록 | 비회원, 회원 | 판매 중인 원두를 조회하고 원하는 원두를 찾는 화면 | 원두 목록 조회, 이름 검색, 원산지·가격·로스팅 정도 필터, 상세 화면 이동 | Browse Coffee Beans, Search by Name, Filter by Origin/Price/Roast Level |
| SCR-02 | 원두 상세 | 비회원, 회원 | 선택한 원두의 상세 정보와 판매 옵션을 확인하는 화면 | 원두 정보 조회, 용량·분쇄도·수량 선택, 품절 여부 확인, 장바구니 담기 | View Bean Details, Add to Cart |
| SCR-03 | 로그인 | 비회원 | 회원이 이메일과 비밀번호로 로그인하는 화면 | 이메일·비밀번호 입력, 로그인, 회원가입 화면 이동 | Log In |
| SCR-04 | 회원가입 | 비회원 | 비회원이 회원 정보를 입력하여 계정을 생성하는 화면 | 회원정보 입력, 회원가입 | Sign Up |
| SCR-05 | 장바구니 | 회원 | 장바구니에 담은 원두와 선택 옵션을 확인하고 관리하는 화면 | 장바구니 조회, 수량 변경, 상품 삭제, 주문 진행 | Manage Cart, View Cart, Change Quantity, Remove Item |
| SCR-06 | 주문/결제 | 회원 | 주문 상품과 배송지를 확인하고 결제를 진행하는 화면 | 주문 상품 확인, 저장된 배송지 선택, 새 배송지 입력, 주문 금액 확인, 결제 및 결제 재시도 | Place Order, Review Order, Select Shipping Address, Enter New Address, Make Payment, Retry Payment |
| SCR-07 | 주문 목록 | 회원 | 회원이 자신의 주문 내역과 현재 상태를 확인하는 화면 | 주문 목록 조회, 주문 상태 확인, 주문 상세 화면 이동 | Manage My Orders, View Order List |
| SCR-08 | 주문 상세 | 회원 | 선택한 주문의 상품·결제·배송 정보를 확인하는 화면 | 주문 상세 조회, 배송 상태 및 송장번호 확인, 배송 추적, 주문 취소 요청 | View Order Details, Track Delivery, Cancel Order |
| SCR-09 | 회원정보 관리 | 회원 | 회원의 개인정보를 조회하고 수정하는 화면 | 이름·연락처 조회 및 수정 | Manage Account, Edit Profile |
| SCR-10 | 배송지 관리 | 회원 | 회원이 저장된 배송지를 관리하는 화면 | 배송지 목록 조회, 배송지 추가·수정, 기본 배송지 설정 | Manage Account, Add Address, Edit Address |
| SCR-11 | 관리자 원두 목록/관리 | 관리자 | 관리자가 판매 원두를 조회하고 관리하는 화면 | 전체 원두 조회, 등록·수정 화면 이동, 재고 확인, 판매 상태 변경 | Manage Products, View Products, Change Sales Status |
| SCR-12 | 관리자 원두 등록/수정 | 관리자 | 관리자가 원두 정보와 판매 옵션을 등록하거나 수정하는 화면 | 원두 등록·수정, 용량·분쇄도 옵션 관리, 옵션별 재고 조정, 품절 처리 | Register Product, Edit Product, Update Stock, Mark as Sold Out |
| SCR-13 | 관리자 주문 목록 | 관리자 | 관리자가 전체 주문과 처리 상태를 확인하는 화면 | 전체 주문 조회, 주문 상태 및 취소 요청 확인, 주문 상세 화면 이동 | Manage Orders, View Orders |
| SCR-14 | 관리자 주문 상세/배송 처리 | 관리자 | 관리자가 개별 주문을 확인하고 배송 및 취소 업무를 처리하는 화면 | 주문 상세 확인, 배송 준비, 택배사·송장번호 등록, 배송 상태 변경, 취소 요청 처리 | Prepare Shipment, Update Delivery Status, Process Cancellation |
