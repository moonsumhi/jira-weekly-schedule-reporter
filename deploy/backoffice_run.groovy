pipeline {
    agent any
    parameters {
        string(name: 'TAG', defaultValue: 'latest', description: 'Run 할 이미지 태그')
        string(name: 'IP', defaultValue: '', description: '배포 서버 IP (비우면 Jenkins Global Env의 BO_APP_SERVER 사용)')
    }
    stages {

        stage('1. Docker Run') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ssh_jenkins',
                        keyFileVariable: 'SSH_KEY'
                    ),
                    usernamePassword(credentialsId: 'admin',
                        usernameVariable: 'HB_USER',
                        passwordVariable: 'HB_PW'),
                    usernamePassword(credentialsId: 'Git_account',
                        usernameVariable: 'GIT_USER',
                        passwordVariable: 'GIT_TOKEN'),
                ]) {
                    sh """
                        ssh -i ${SSH_KEY} -p 50022 -o StrictHostKeyChecking=no jenkins@${params.IP ?: env.BO_APP_SERVER} '
                            export XDG_RUNTIME_DIR=/run/user/\$(id -u)

                            echo "===== 작업 디렉토리로 이동 ====="
                            cd /home/jenkins/backoffice
                            pwd
                            hostname

                            echo "===== docker-compose.yml 최신화 ====="
                            git fetch http://${GIT_USER}:${GIT_TOKEN}@${env.GIT_SERVER}/${env.BO_GIT_REPO} main
                            git checkout FETCH_HEAD -- docker-compose.yml

                            echo "===== Harbor 로그인 ====="
                            echo "${HB_PW}" | docker login ${env.HARBOR_URL} \
                                --username "${HB_USER}" \
                                --password-stdin

                            echo "===== docker compose down ====="
                            docker compose down || true

                            echo "===== docker pull ====="
                            docker pull ${env.HARBOR_URL}/dev/jira-reporter-frontend:${params.TAG}
                            docker pull ${env.HARBOR_URL}/dev/jira-reporter-backend:${params.TAG}
                            docker pull ${env.HARBOR_URL}/dev/mongo:latest
                            docker pull ${env.HARBOR_URL}/dev/mongo-express:latest

                            echo "===== docker compose up ====="
                            TAG=${params.TAG} docker compose up -d --no-build

                            sleep 10
                            docker ps
                        '
                    """
                }
            }
        }
    }
    post {
        success {
            echo "성공."
        }
        failure {
            echo "실패"
        }
    }
}
