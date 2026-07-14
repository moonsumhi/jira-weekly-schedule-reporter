
pipeline {
    agent any

    parameters {
        string(name: 'BRANCH', defaultValue: 'main', description: '빌드할 브랜치 (예: main, dev)')
    }

    stages {

        stage('Build 서버에서 전체 작업 수행') {
            environment {
                SAFE_BRANCH = "${params.BRANCH.replace('/', '-')}"
            }
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
ssh -i \${SSH_KEY} -p 50022 -o StrictHostKeyChecking=no jenkins@${env.BUILD_SERVER} <<ENDSSH

set -e

echo "===== 1. 기존 디렉토리 삭제 ====="
rm -rf ${env.REMOTE_DIR}

echo "===== 2. Git Clone (Build 서버에서 수행) ====="
git clone -b ${params.BRANCH} http://\${GIT_USER}:\${GIT_TOKEN}@${env.GIT_SERVER}/${env.BO_GIT_REPO} ${env.REMOTE_DIR}

cd ${env.REMOTE_DIR}

echo "===== 3. Harbor 로그인 ====="
echo "\${HB_PW}" | docker login ${env.HARBOR_URL} --username "\${HB_USER}" --password-stdin --tls-verify=false

echo "===== 4. 이미지 빌드 ====="
docker build -f ${env.REMOTE_DIR}/Dockerfile --build-arg BASE_IMAGE=${env.HARBOR_URL}/dev/python-base:3.12-slim --build-arg SKIP_SYS_DEPS=true --build-arg PIP_INDEX_URL=${env.PIP_INDEX_URL} -t ${env.HARBOR_URL}/dev/jira-reporter-backend:${env.SAFE_BRANCH}-${params.TAG} ${env.REMOTE_DIR}/

docker build -f ${env.REMOTE_DIR}/frontend/optool/Dockerfile --build-arg NODE_BASE_IMAGE=${env.HARBOR_URL}/dev/node-base:22-alpine --build-arg NGINX_BASE_IMAGE=${env.HARBOR_URL}/dev/nginx:alpine --build-arg SKIP_NPM_INSTALL=true -t ${env.HARBOR_URL}/dev/jira-reporter-frontend:${env.SAFE_BRANCH}-${params.TAG} ${env.REMOTE_DIR}/

echo "===== 5. Push ====="
docker push ${env.HARBOR_URL}/dev/jira-reporter-frontend:${env.SAFE_BRANCH}-${params.TAG} --tls-verify=false
docker push ${env.HARBOR_URL}/dev/jira-reporter-backend:${env.SAFE_BRANCH}-${params.TAG} --tls-verify=false
docker logout ${env.HARBOR_URL}

ENDSSH
                    """
                }
            }
        }
    }
}
