"""Fixed courier list and tracking links (SDD 6.10, FR-35). The front end knows no URLs."""

from urllib.parse import quote

from orders.models import Courier

URL_TEMPLATES = {
    Courier.CJ: "https://trace.cjlogistics.com/next/tracking.html?wblNo={n}",
    Courier.HANJIN: (
        "https://www.hanjin.com/kor/CMS/DeliveryMgr/WaybillResult.do"
        "?mCode=MN038&schLang=KR&wblnumText2={n}"
    ),
    Courier.LOTTE: "https://www.lotteglogis.com/home/reservation/tracking/linkView?InvNo={n}",
    Courier.EPOST: "https://service.epost.go.kr/trace.RetrieveDomRigiTraceList.comm?sid1={n}",
    Courier.LOGEN: "https://www.ilogen.com/web/personal/trace/{n}",
}


def courier_name(code):
    return Courier(code).label if code else None


def tracking_url(code, tracking_number):
    if not code or not tracking_number:
        return None
    number = quote(tracking_number.replace("-", ""), safe="")
    return URL_TEMPLATES[Courier(code)].format(n=number)
