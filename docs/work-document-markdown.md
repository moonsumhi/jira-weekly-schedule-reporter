현재 상태: 상세의 내보내기 메뉴에서 Markdown(.md), 한글(.hwp), Word(.docx)를 선택한다. HWP/Word는 인증이 필요한 `POST /form-entries/export-document`에 형식과 `original_form`(제목·섹션·원본 필드 데이터)을 전달해 생성한다. 저장된 Markdown 스냅샷 대신 원본 필드로 표를 만들며, 작업 대상의 비고는 HOSTNAME 다음에 배치한다. 셀 안의 문단·사진·중첩 표를 유지한다. 이는 앱의 원본 양식을 문서로 구성하는 기능이며, Import 전 파일의 페이지 배치를 그대로 복제하는 기능은 아니다. 원본 필드가 없는 기존 Markdown 전용 문서는 Markdown으로 변환한다. 문서 데이터를 변경하지 않는다. Word는 python-docx를, HWP는 기존 로컬 변환기를 사용한다. 외부 이미지 URL은 가져오지 않는다. 아래 예전 GET 내보내기 함수는 내부 보존 코드이며 라우트로 등록하지 않는다.

# 작업관리 Markdown 문서

## 원본 양식과 Markdown 보기

작업관리에서 새 문서는 원본 양식으로 작성한다. 항목별 원본 데이터가 있는 문서는 수정 시 그 양식을 유지하며, 저장 요청에 원본 항목과 자동 생성한 `문서 본문`을 함께 포함한다. 서버는 같은 문서 버전으로 저장하고 Markdown 파일도 생성한다. 상세의 `원본 양식` / `Markdown 보기`는 같은 저장 버전의 두 표현이며 과거 버전 이력은 아니다. Markdown 보기는 원본 양식에서 수정 후 저장할 때 갱신된다.

이미 Markdown으로만 저장된 문서는 자동 변경하지 않으며 기존 Markdown 편집을 유지한다. 새 Import는 항목별 원본 양식으로 매핑한다. 원본 데이터가 있는 문서의 Markdown을 별도로 편집하는 기능은 제공하지 않는다.

작업관리의 신규 문서는 문서 종류를 선택한 뒤 원본 양식으로 작성한다. HWP, HWPX, DOC, DOCX, PDF Import는 `POST /form-entries/import-form`에 파일과 `template_id`를 전송한다. 변환 결과를 양식의 항목에 매핑하고 원본 양식 편집 화면에서 확인한 후 저장한다. 글·사진은 textarea 필드의 Markdown으로 순서를 유지한다. 매핑되지 않는 부분은 `가져온 추가 내용`에 보존하고 상세·수정·Markdown 생성에 포함한다. Import 자체는 문서를 생성하지 않으며 사용자가 저장할 때 생성한다.

- `POST /form-entries/import-markdown`: 인증된 사용자에게 변환된 Markdown과 변환 안내를 반환한다. 파일 최대 크기는 50MB이다. Import만으로 문서 목록에 등록하지 않는다.
- `POST /form-entries/import-form`은 Import에 사용한 원본 파일(HWP/HWPX/DOC/DOCX/PDF)을 함께 보존한다. 상세의 `원본 파일 다운로드` 버튼은 저장된 파일을 그대로 내려받으며, HWP 내보내기는 추출된 원본 필드에서 새로 생성되므로 PDF의 페이지 배치와 동일하지 않을 수 있다.
- 기존 생성·수정 API는 `data["문서 본문"][0]`에 제목, 작업 일시, 내용, `내용__format=markdown`을 저장한다. 본문은 `/app/uploads/work_documents/markdown/<uuid>.md`에도 UTF-8로 저장하며 DB의 `markdown_file`이 해당 저장본을 가리킨다. 매 저장마다 새 파일을 만든다.
- 상세 화면의 `Markdown 수정`은 본문을 직접 편집해 저장하며, 원본 양식 데이터는 유지한 채 `__markdown_override=true` 표시로 Markdown 버전을 우선 사용한다. 이후 원본 양식 수정으로 저장하면 다시 양식 데이터에서 Markdown을 생성한다.
- 사진은 업로드 디렉터리에 따로 저장하고 Markdown에서 상대 URL로 참조한다. `.md` 내보내기에서는 서버의 절대 URL로 바꾼다.
- `GET /form-entries/{entry_id}/export-hwpx`: 저장된 Markdown에서 한글 표준 문서 `.hwpx`를 생성한다. 사진은 서버 업로드 파일에서 읽어 HWPX 안에 포함한다. 외부 URL은 요청하지 않는다.
- HWP 내보내기 전에는 `hwp edit --style-tables report`를 적용해 표 머리글 음영, 내용에 맞춘 열 너비와 정렬을 보정한다. 원본 HWP의 셀 병합과 인쇄 배치를 그대로 복원하는 방식은 아니며, 원본 양식 보존이 필요하면 저장된 원본 파일 다운로드를 사용한다.
- 기존 항목별 문서는 상세와 수정에서 원본 양식을 유지한다. 저장 시 기존 이미지도 업로드 URL로 변환하고 원본 항목과 Markdown을 함께 보존한다.

HWP의 표·문단·그림 순서는 HTML 변환 결과를, Word는 문서의 요소 순서를 사용한다. PDF는 페이지의 텍스트·이미지 블록 위치를 기준으로 읽는다. 텍스트가 없는 PDF 페이지는 페이지 이미지로 보존하며 OCR은 수행하지 않는다. 글꼴, 페이지 배치, 병합 표, 복잡한 도형의 원본과 동일한 재현은 보장하지 않는다. 다단 PDF의 읽기 순서와 복잡한 표는 Import 후 확인이 필요하다.

화면의 한글 내보내기는 `GET /form-entries/{entry_id}/export-hwp`를 사용한다. Markdown에서 HWPX를 생성한 뒤 서버 내부의 [hwp-cli v0.17.0](https://github.com/STAIxBWLB/hwp-cli)로 실제 바이너리 `.hwp`로 변환한다. Docker 빌드에서 Linux x86_64 실행 파일을 SHA-256 검증 후 설치하며 Apache-2.0 라이선스는 `docs/third-party/hwp-cli-LICENSE.txt`에 포함한다. 외부 서비스에 문서를 전송하지 않는다. 기존 HWPX API도 유지한다.

첨부된 HWPX는 UTF-8 한글이 정상이었지만 설치된 한글 2010에서는 ZIP 내용을 텍스트로 표시했다. 변환한 HWP는 같은 프로그램에서 한글과 표가 표시됨을 확인했다. 상위 버전 문서라는 안내는 나타날 수 있다. 일반 표, 본문, 제목 및 사진을 내보내며 원본 문서의 인쇄 양식을 복원하는 기능은 아니다.

검증: `tests/test_work_documents.py`는 Word→Markdown→HWPX→Markdown 글/사진 순서, 표 안의 사진, HWPX 스키마, 스캔 PDF 보존, 실제 Markdown 파일 저장 및 생성·수정·내보내기 API를 확인한다.
