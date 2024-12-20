import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# 컨테이너 정보 (단위: mm)
CONTAINERS = {
    "20ft": {"length": 5898, "width": 2352, "height": 2395},
    "40ft": {"length": 12021, "width": 2352, "height": 2395},
    "40ft HC": {"length": 12021, "width": 2352, "height": 2691},
}

def calculate_cartons(per_carton, order_qty):
    return math.ceil(order_qty / per_carton)

def calculate_cbm(length, width, height, quantity):
    return (length * width * height * quantity) / 1e9  # mm³을 m³으로 변환

def add_box(fig, x0, y0, z0, dx, dy, dz, color, name):
    # 8개의 꼭짓점 정의
    vertices = np.array([
        [x0, y0, z0],
        [x0 + dx, y0, z0],
        [x0 + dx, y0 + dy, z0],
        [x0, y0 + dy, z0],
        [x0, y0, z0 + dz],
        [x0 + dx, y0, z0 + dz],
        [x0 + dx, y0 + dy, z0 + dz],
        [x0, y0 + dy, z0 + dz]
    ])

    # 면 추가 (Mesh3d)
    I = [0, 0, 0, 1, 1, 2, 4, 4, 4, 5, 5, 6]
    J = [1, 3, 4, 2, 3, 3, 5, 6, 7, 6, 7, 7]
    K = [3, 4, 5, 3, 7, 7, 6, 7, 5, 7, 4, 5]

    fig.add_trace(go.Mesh3d(
        x=vertices[:, 0],
        y=vertices[:, 1],
        z=vertices[:, 2],
        i=I,
        j=J,
        k=K,
        color=color,
        opacity=0.7,
        name=name
    ))

    # 외곽선 추가 (Scatter3d)
    lines = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # 바닥면
        [4, 5], [5, 6], [6, 7], [7, 4],  # 윗면
        [0, 4], [1, 5], [2, 6], [3, 7]   # 세로선
    ]

    for line in lines:
        fig.add_trace(go.Scatter3d(
            x=[vertices[line[0]][0], vertices[line[1]][0]],
            y=[vertices[line[0]][1], vertices[line[1]][1]],
            z=[vertices[line[0]][2], vertices[line[1]][2]],
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False
        ))

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)  # mm³을 m³으로 변환

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0
    total_loaded_boxes = 0
    box_color = '#DEB887'  # 황토색

    product_report = []

    for i, (bx, by, bz, cartons, per_carton, name) in enumerate(boxes):
        box_count = 0
        for _ in range(cartons):
            # 공간 초과 시 다음 행으로 이동
            if current_x + bx > cx:
                current_x = 0
                current_y += by

            # 공간 초과 시 다음 층으로 이동
            if current_y + by > cy:
                current_y = 0
                current_z += bz

            # 공간 초과 시 더 이상 배치 불가
            if current_z + bz > cz:
                st.warning(f"⚠️ 컨테이너에 더 이상 {name} 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            add_box(fig, current_x, current_y, current_z, bx, by, bz, box_color, name)
            used_cbm += (bx * by * bz) / 1e9  # mm³을 m³으로 변환
            total_loaded_boxes += 1
            box_count += 1

            # 다음 박스의 x 좌표 업데이트
            current_x += bx

        # 제품별 CBM 및 전체 제품 수 계산
        product_cbm = (bx * by * bz * box_count) / 1e9
        total_products = per_carton * box_count
        product_report.append({
            "제품명": name,
            "선적된 박스 수": box_count,
            "전체 제품 수": total_products,
            "제품별 CBM": f"{product_cbm:.2f} m³"
        })

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
            aspectmode='data'
        ),
        margin=dict(r=10, l=10, b=10, t=50),
        title=f"{container_type} 컨테이너 선적 시뮬레이션"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 결과 요약 출력
    st.subheader("선적 정보 요약")
    total_cbm_used = sum(float(report["제품별 CBM"].split()[0]) for report in product_report)
    remaining_cbm = container_cbm - total_cbm_used

    st.write(f"**사용된 CBM:** {total_cbm_used:.2f} m³")
    st.write(f"**남은 CBM:** {remaining_cbm:.2f} m³")

    # 추가 선적 가능 박스 수 계산
    st.write("**추가 선적 가능 박스 수 시뮬레이션:**")
    for report in product_report:
        if report["제품별 CBM"] == "0.00 m³":
            possible_boxes = 0
        else:
            # 단일 박스의 CBM
            single_cbm = float(report["제품별 CBM"].split()[0]) / report["선적된 박스 수"] if report["선적된 박스 수"] > 0 else 0
            possible_boxes = math.floor(remaining_cbm / single_cbm) if single_cbm > 0 else 0
        st.write(f"- **{report['제품명']}**: 추가로 {possible_boxes} 박스 선적 가능")

    st.write("\n")

    st.table(product_report)

    # PDF 생성 함수
    def create_pdf(container_type, container_dim, boxes, container_cbm, product_report, total_cbm_used, remaining_cbm):
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
        pdf.drawString(70, 590, "추가 선적 가능 박스 수:")
        y = 570
        for report in product_report:
            single_cbm = float(report["제품별 CBM"].split()[0]) / report["선적된 박스 수"] if report["선적된 박스 수"] > 0 else 0
            possible_boxes = math.floor(remaining_cbm / single_cbm) if single_cbm > 0 else 0
            pdf.drawString(90, y, f"- {report['제품명']}: 추가로 {possible_boxes} 박스 선적 가능")
            y -= 20

        # 제품 정보
        y -= 20
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, "제품 정보:")
        pdf.setFont("Helvetica", 12)
        y -= 20

        for i, report in enumerate(product_report):
            pdf.drawString(50, y, f"{i + 1}. 제품명: {report['제품명']}")
            pdf.drawString(70, y - 20, f"선적된 박스 수: {report['선적된 박스 수']}")
            pdf.drawString(70, y - 40, f"전체 제품 수: {report['전체 제품 수']}")
            pdf.drawString(70, y - 60, f"제품별 CBM: {report['제품별 CBM']}")
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
            buffer = create_pdf(container_type, container_dim, boxes, container_cbm, product_report, total_cbm_used, remaining_cbm)
            st.download_button(
                label="PDF 다운로드",
                data=buffer,
                file_name="YNK_shipping_simulation.pdf",
                mime="application/pdf"
            )
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# 컨테이너 정보 (단위: mm)
CONTAINERS = {
    "20ft": {"length": 5898, "width": 2352, "height": 2395},
    "40ft": {"length": 12021, "width": 2352, "height": 2395},
    "40ft HC": {"length": 12021, "width": 2352, "height": 2691},
}

def calculate_cartons(per_carton, order_qty):
    return math.ceil(order_qty / per_carton)

def calculate_cbm(length, width, height, quantity):
    return (length * width * height * quantity) / 1e9  # mm³을 m³으로 변환

def add_box(fig, x0, y0, z0, dx, dy, dz, color, name):
    # 8개의 꼭짓점 정의
    vertices = np.array([
        [x0, y0, z0],
        [x0 + dx, y0, z0],
        [x0 + dx, y0 + dy, z0],
        [x0, y0 + dy, z0],
        [x0, y0, z0 + dz],
        [x0 + dx, y0, z0 + dz],
        [x0 + dx, y0 + dy, z0 + dz],
        [x0, y0 + dy, z0 + dz]
    ])

    # 면 추가 (Mesh3d)
    I = [0, 0, 0, 1, 1, 2, 4, 4, 4, 5, 5, 6]
    J = [1, 3, 4, 2, 3, 3, 5, 6, 7, 6, 7, 7]
    K = [3, 4, 5, 3, 7, 7, 6, 7, 5, 7, 4, 5]

    fig.add_trace(go.Mesh3d(
        x=vertices[:, 0],
        y=vertices[:, 1],
        z=vertices[:, 2],
        i=I,
        j=J,
        k=K,
        color=color,
        opacity=0.7,
        name=name
    ))

    # 외곽선 추가 (Scatter3d)
    lines = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # 바닥면
        [4, 5], [5, 6], [6, 7], [7, 4],  # 윗면
        [0, 4], [1, 5], [2, 6], [3, 7]   # 세로선
    ]

    for line in lines:
        fig.add_trace(go.Scatter3d(
            x=[vertices[line[0]][0], vertices[line[1]][0]],
            y=[vertices[line[0]][1], vertices[line[1]][1]],
            z=[vertices[line[0]][2], vertices[line[1]][2]],
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False
        ))

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)  # mm³을 m³으로 변환

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0
    total_loaded_boxes = 0
    box_color = '#DEB887'  # 황토색

    product_report = []

    for i, (bx, by, bz, cartons, per_carton, name) in enumerate(boxes):
        box_count = 0
        for _ in range(cartons):
            # 공간 초과 시 다음 행으로 이동
            if current_x + bx > cx:
                current_x = 0
                current_y += by

            # 공간 초과 시 다음 층으로 이동
            if current_y + by > cy:
                current_y = 0
                current_z += bz

            # 공간 초과 시 더 이상 배치 불가
            if current_z + bz > cz:
                st.warning(f"⚠️ 컨테이너에 더 이상 {name} 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            add_box(fig, current_x, current_y, current_z, bx, by, bz, box_color, name)
            used_cbm += (bx * by * bz) / 1e9  # mm³을 m³으로 변환
            total_loaded_boxes += 1
            box_count += 1

            # 다음 박스의 x 좌표 업데이트
            current_x += bx

        # 제품별 CBM 및 전체 제품 수 계산
        product_cbm = (bx * by * bz * box_count) / 1e9
        total_products = per_carton * box_count
        product_report.append({
            "제품명": name,
            "선적된 박스 수": box_count,
            "전체 제품 수": total_products,
            "제품별 CBM": f"{product_cbm:.2f} m³"
        })

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
            aspectmode='data'
        ),
        margin=dict(r=10, l=10, b=10, t=50),
        title=f"{container_type} 컨테이너 선적 시뮬레이션"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 결과 요약 출력
    st.subheader("선적 정보 요약")
    total_cbm_used = sum(float(report["제품별 CBM"].split()[0]) for report in product_report)
    remaining_cbm = container_cbm - total_cbm_used

    st.write(f"**사용된 CBM:** {total_cbm_used:.2f} m³")
    st.write(f"**남은 CBM:** {remaining_cbm:.2f} m³")

    # 추가 선적 가능 박스 수 계산
    st.write("**추가 선적 가능 박스 수 시뮬레이션:**")
    for report in product_report:
        if report["제품별 CBM"] == "0.00 m³":
            possible_boxes = 0
        else:
            # 단일 박스의 CBM
            single_cbm = report["제품별 CBM"] / report["선적된 박스 수"]
            possible_boxes = math.floor(remaining_cbm / single_cbm) if single_cbm > 0 else 0
        st.write(f"- **{report['제품명']}**: 추가로 {possible_boxes} 박스 선적 가능")

    st.write("\n")

    st.table(product_report)

    # PDF 생성 함수
    def create_pdf(container_type, container_dim, boxes, container_cbm, product_report, total_cbm_used, remaining_cbm):
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
        pdf.drawString(70, 590, "추가 선적 가능 박스 수:")
        y = 570
        for report in product_report:
            single_cbm = float(report["제품별 CBM"].split()[0]) / report["선적된 박스 수"] if report["선적된 박스 수"] > 0 else 0
            possible_boxes = math.floor(remaining_cbm / single_cbm) if single_cbm > 0 else 0
            pdf.drawString(90, y, f"- {report['제품명']}: 추가로 {possible_boxes} 박스 선적 가능")
            y -= 20

        # 제품 정보
        y -= 20
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, "제품 정보:")
        pdf.setFont("Helvetica", 12)
        y -= 20

        for i, report in enumerate(product_report):
            pdf.drawString(50, y, f"{i + 1}. 제품명: {report['제품명']}")
            pdf.drawString(70, y - 20, f"선적된 박스 수: {report['선적된 박스 수']}")
            pdf.drawString(70, y - 40, f"전체 제품 수: {report['전체 제품 수']}")
            pdf.drawString(70, y - 60, f"제품별 CBM: {report['제품별 CBM']}")
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
            pdf.drawString(70, 590, "추가 선적 가능 박스 수:")
            y = 570
            for report in product_report:
                single_cbm = float(report["제품별 CBM"].split()[0]) / report["선적된 박스 수"] if report["선적된 박스 수"] > 0 else 0
                possible_boxes = math.floor(remaining_cbm / single_cbm) if single_cbm > 0 else 0
                pdf.drawString(90, y, f"- {report['제품명']}: 추가로 {possible_boxes} 박스 선적 가능")
                y -= 20
    
            # 제품 정보
            y -= 20
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(50, y, "제품 정보:")
            pdf.setFont("Helvetica", 12)
            y -= 20
    
            for i, report in enumerate(product_report):
                pdf.drawString(50, y, f"{i + 1}. 제품명: {report['제품명']}")
                pdf.drawString(70, y - 20, f"선적된 박스 수: {report['선적된 박스 수']}")
                pdf.drawString(70, y - 40, f"전체 제품 수: {report['전체 제품 수']}")
                pdf.drawString(70, y - 60, f"제품별 CBM: {report['제품별 CBM']}")
                y -= 80
    
            pdf.showPage()
            pdf.save()
    
            buffer.seek(0)
            st.download_button(
                label="PDF 다운로드",
                data=buffer,
                file_name="YNK_shipping_simulation.pdf",
                mime="application/pdf"
            )
