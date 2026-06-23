
pipeline {
    agent any

    environment {
        BUILD_SERVER = 'x.x.x.x(BUILD_SERVER)'
        GIT_URL      = 'http://x.x.x.x(GIT_SERVER)/ncdc-source-code/ncdc-backoffice.git'
        REMOTE_DIR   = '/home/jenkins/backoffice'
        HARBOR_URL   = 'x.x.x.x(HARBOR_URL)'
        buildTag     = "${params.TAG}"
    }

    stages {

        stage('Build 서버에서 전체 작업 수행') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: 'jenkins-build',
                                      keyFileVariable: 'SSH_KEY'),
                    usernamePassword(credentialsId: 'Git_account',
                                     usernameVariable: 'GIT_USER',
                                     passwordVariable: 'GIT_TOKEN'),
                    usernamePassword(credentialsId: 'admin',
                                     usernameVariable: 'HB_USER',
                                     passwordVariable: 'HB_PW')
                ]) {

                    sh """
                    ssh -i ${SSH_KEY} -p 50022 -o StrictHostKeyChecking=no \
                    jenkins@${BUILD_SERVER} <<EOF

                    set -e

                    echo "===== 1. 기존 디렉토리 삭제 ====="
                    rm -rf ${REMOTE_DIR}

                    echo "===== 2. Git Clone (Build 서버에서 수행) ====="
                    git clone -b main http://${GIT_USER}:${GIT_TOKEN}@x.x.x.x(GIT_SERVER)/ncdc-source-code/ncdc-backoffice.git ${REMOTE_DIR}

                    cd ${REMOTE_DIR}

                    hostname

                    echo "===== 3. Harbor 로그인 ====="
                    echo "${HB_PW}" | docker login ${HARBOR_URL} \
                        --username "${HB_USER}" \
                        --password-stdin \
                        --tls-verify=false

                    hostname
                    pwd

                    echo "===== 4. 이미지 빌드 ====="
                    echo "백엔드 빌드 시작"
                    docker build -f /home/jenkins/backoffice/Dockerfile \
                        --build-arg BASE_REGISTRY=${HARBOR_URL} \
                        -t ${HARBOR_URL}/dev/jira-reporter-backend:${params.TAG} \
                        /home/jenkins/backoffice/
                    echo "백엔드 빌드 완료 및 프론트엔드 빌드 시작"

                    docker build -f /home/jenkins/backoffice/frontend/optool/Dockerfile \
                        --build-arg BASE_REGISTRY=${HARBOR_URL} \
                        -t ${HARBOR_URL}/dev/jira-reporter-frontend:${params.TAG} \
                        /home/jenkins/backoffice/
                    echo "프론트엔드 빌드 완료"

                    hostname
                    
                    echo "===== 5. Push ====="

                    docker push ${HARBOR_URL}/dev/jira-reporter-frontend:${params.TAG} --tls-verify=false
                    docker push ${HARBOR_URL}/dev/jira-reporter-backend:${params.TAG} --tls-verify=false
                    docker logout ${HARBOR_URL}

                    """
                }
            }
        }
    }
}
