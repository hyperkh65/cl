# PDF 생성 함수
def create_pdf(container_type, container_dim, product_report, total_cbm_used, remaining_cbm):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("YNK 선적 시뮬레이션")

    # 타이틀
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(200, 750, "YNK 선적 시뮬레이션 보고서")

    # 컨테이너 정보
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 720, f"컨테이너 타입: {container_type}")
    pdf.drawString(50, 700, f"내부 치수: {container_dim['length']} x {container_dim['width']} x {container_dim['height']} mm")
    pdf.drawString(50, 680, f"총 CBM: {container_cbm:.2f} m³")

    # 선적 정보 요약
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 650, "선적 정보 요약:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(70, 630, f"사용된 CBM: {total_cbm_used:.2f} m³")
    pdf.drawString(70, 610, f"남은 CBM: {remaining_cbm:.2f} m³")
    pdf.drawString(70, 590, "제품별 선적 정보:")
    y = 570
    for report in product_report:
        pdf.drawString(90, y, f"- {report['제품명']}:")
        pdf.drawString(110, y - 20, f"선적된 박스 수: {report['선적된 박스 수']}")
        pdf.drawString(110, y - 40, f"전체 제품 수: {report['전체 제품 수']}")
        pdf.drawString(110, y - 60, f"제품별 CBM: {report['제품별 CBM']}")
        y -= 80

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer

# PDF 다운로드 버튼
if st.button("PDF로 출력"):
    if len(product_report) == 0:
        st.warning("시뮬레이션을 먼저 실행해주세요.")
    else:
        buffer = create_pdf(container_type, container_dim, product_report, total_cbm_used, remaining_cbm)
        st.download_button(
            label="PDF 다운로드",
            data=buffer,
            file_name="YNK_shipping_simulation.pdf",
            mime="application/pdf"
        )
