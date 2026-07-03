
pipeline {
    agent any

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
                    jenkins@${env.BUILD_SERVER} <<EOF

                    set -e

                    echo "===== 1. 기존 디렉토리 삭제 ====="
                    rm -rf ${env.REMOTE_DIR}

                    echo "===== 2. Git Clone (Build 서버에서 수행) ====="
                    git clone -b main http://${GIT_USER}:${GIT_TOKEN}@${env.GIT_SERVER}/${env.BO_GIT_REPO} ${env.REMOTE_DIR}

                    cd ${env.REMOTE_DIR}

                    hostname

                    echo "===== 3. Harbor 로그인 ====="
                    echo "${HB_PW}" | docker login ${env.HARBOR_URL} \
                        --username "${HB_USER}" \
                        --password-stdin \
                        --tls-verify=false

                    hostname
                    pwd

                    echo "===== 4. 이미지 빌드 ====="
                    echo "백엔드 빌드 시작"
                    docker build -f ${env.REMOTE_DIR}/Dockerfile \
                        --build-arg BASE_IMAGE=${env.BO_BASE_IMAGE} \
                        --build-arg SKIP_SYS_DEPS=${env.BO_SKIP_SYS_DEPS} \
                        -t ${env.HARBOR_URL}/dev/jira-reporter-backend:${params.TAG} \
                        ${env.REMOTE_DIR}/
                    echo "백엔드 빌드 완료 및 프론트엔드 빌드 시작"

                    docker build -f ${env.REMOTE_DIR}/frontend/optool/Dockerfile \
                        --build-arg BASE_REGISTRY=${env.HARBOR_URL} \
                        -t ${env.HARBOR_URL}/dev/jira-reporter-frontend:${params.TAG} \
                        ${env.REMOTE_DIR}/
                    echo "프론트엔드 빌드 완료"

                    hostname

                    echo "===== 5. Push ====="
                    docker push ${env.HARBOR_URL}/dev/jira-reporter-frontend:${params.TAG} --tls-verify=false
                    docker push ${env.HARBOR_URL}/dev/jira-reporter-backend:${params.TAG} --tls-verify=false
                    docker logout ${env.HARBOR_URL}

                    EOF
                    """
                }
            }
        }
    }
}
