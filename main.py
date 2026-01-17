from __future__ import annotations

from io import BytesIO
from typing import Tuple

import streamlit as st
from pypdf import PdfReader, PdfWriter


def is_page_blank(page) -> bool:
    """
    텍스트, 이미지, 주석이 하나라도 있으면 False를 반환.
    """

    # 텍스트가 있으면 즉시 비어있지 않은 것으로 판단
    text = (page.extract_text() or "").strip()
    if text:
        return False

    # 주석(하이라이트, 메모 등)이 있다면 비어있지 않음
    if page.get("/Annots"):
        return False

    # 페이지 리소스에 이미지 XObject가 포함되어 있는지 확인
    resources = page.get("/Resources")
    if resources:
        xobjects = resources.get("/XObject")
        if xobjects:
            try:
                for _, xobject in xobjects.get_object().items():
                    if xobject.get("/Subtype") == "/Image":
                        return False
            except Exception:
                # 일부 PDF는 파싱이 불안정할 수 있으므로 건너뜀
                pass

    return True


def remove_blank_pages(pdf_bytes: bytes) -> Tuple[bytes, int, int]:
    """
    PDF 바이트에서 빈 페이지를 제거한 새 PDF 바이트와 총/삭제 페이지 수를 반환.
    """

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    total_pages = len(reader.pages)
    removed_pages = 0

    for page in reader.pages:
        if is_page_blank(page):
            removed_pages += 1
            continue
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.read(), total_pages, removed_pages


def run_app() -> None:
    """
    Streamlit UI: PDF 업로드 → 빈 페이지 제거 → 바로 다운로드.
    """

    # Streamlit 기본 테마/스타일을 그대로 사용해 간단하고 안정적으로 구성합니다.
    st.set_page_config(page_title="PDF 빈 페이지 제거기")
    st.title("PDF 빈 페이지 제거기")
    st.caption("업로드한 PDF에서 빈 페이지를 찾아 제거한 뒤, 바로 다운로드합니다.")

    # 사이드바: 사용 방법과 동작 원리를 간단히 안내
    with st.sidebar:
        st.subheader("사용 방법")
        st.markdown(
            """
            1) PDF를 업로드합니다.
            2) **빈 페이지 제거 실행** 버튼을 누릅니다.
            3) 결과 요약을 확인한 뒤 다운로드합니다.
            """
        )
        st.subheader("빈 페이지 판단 기준")
        st.markdown(
            """
            아래 항목 중 하나라도 있으면 **빈 페이지가 아닌 것으로 판단**해 유지합니다.
            - 텍스트
            - 이미지(XObject)
            - 주석(하이라이트/메모 등)
            """
        )
        st.subheader("주의")
        st.markdown(
            """
            - 비밀번호로 보호된 PDF, 손상된 PDF는 처리 중 오류가 날 수 있습니다.
            - 스캔본(이미지) 문서는 이미지가 감지되므로 보통 삭제되지 않습니다.
            """
        )

    st.markdown(
        """
        업로드한 파일은 브라우저 세션에서만 처리되며, 이 앱은 별도 저장을 하지 않는 것을 전제로 합니다.
        """
    )

    uploaded = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"], max_upload_size=1000)

    if uploaded:
        st.write("선택한 파일:")
        st.code(f"{uploaded.name} ({uploaded.size / (1024 * 1024):.2f} MB)")

    run_clicked = st.button("빈 페이지 제거 실행", type="primary", disabled=uploaded is None)

    if uploaded and run_clicked:
        pdf_bytes = uploaded.getvalue()
        if not pdf_bytes:
            st.warning("업로드된 파일이 비어 있습니다. 다른 파일을 선택해주세요.")
            return

        try:
            with st.spinner("빈 페이지를 감지하는 중입니다..."):
                cleaned_bytes, total_pages, removed_pages = remove_blank_pages(pdf_bytes)
        except Exception as exc:
            st.error("PDF 처리 중 오류가 발생했습니다. 파일이 손상되었거나 보호되어 있을 수 있습니다.")
            st.exception(exc)
            return

        kept_pages = total_pages - removed_pages
        st.success("처리가 완료되었습니다.")
        st.write("결과 요약")
        col1, col2, col3 = st.columns(3)
        col1.metric("총 페이지", total_pages)
        col2.metric("삭제", removed_pages)
        col3.metric("유지", kept_pages)

        st.download_button(
            label="정리된 PDF 다운로드",
            data=cleaned_bytes,
            file_name=f"cleaned_{uploaded.name}",
            mime="application/pdf",
        )

        with st.expander("문제가 생겼나요? (간단한 체크리스트)"):
            st.markdown(
                """
                - PDF가 비밀번호로 보호되어 있지 않은지 확인
                - 파일이 너무 크거나 손상되지 않았는지 확인
                - 다른 PDF 뷰어에서 열리는지 확인
                """
            )


if __name__ == "__main__":
    run_app()
